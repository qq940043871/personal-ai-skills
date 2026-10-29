import java.io.*;
import java.nio.ByteBuffer;
import java.nio.channels.FileChannel;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;

/**
 * Scan primitive-array payloads in an HPROF dump:
 *  - length distribution of char[]/short[]/int[]/byte[] (fixed-size buffer fingerprint)
 *  - keyword scan over char[] text (identify driver/business strings in the heap)
 * Zero-dependency, Java 8+; 8MB direct buffer handles multi-GB dumps.
 *
 * Usage:   java HprofArrays <heap.hprof> [keywords.txt]
 * keywords.txt: one keyword per line; '#' comments allowed. If omitted, the
 * built-in default list is used — it comes from the openGauss SQLWarning-storm
 * case (2026-10 iface OOM). CUSTOMIZE IT for your driver/business before use:
 * include driver exception class names, business table names, protocol words.
 */
public class HprofArrays {
    static FileChannel ch;
    static ByteBuffer bb = ByteBuffer.allocateDirect(8 << 20);
    static long pos = 0, fileSize;
    static { bb.limit(0); }

    static void refill() throws IOException {
        bb.compact();
        int n;
        do { n = ch.read(bb); } while (n == 0);
        if (n < 0) throw new EOFException("EOF at " + pos);
        bb.flip();
    }
    static void need(int k) throws IOException { if (bb.remaining() < k) refill(); }
    static int u1() throws IOException { need(1); pos++; return bb.get() & 0xff; }
    static int u2() throws IOException { need(2); pos += 2; return ((bb.get() & 0xff) << 8) | (bb.get() & 0xff); }
    static long u4() throws IOException { need(4); pos += 4; return bb.getInt() & 0xffffffffL; }
    static long u8() throws IOException { need(8); pos += 8; return bb.getLong(); }
    static void skip(long n) throws IOException {
        if (n <= 0) return;
        int r = bb.remaining();
        if (n <= r) { bb.position(bb.position() + (int) n); pos += n; return; }
        n -= r;
        bb.position(bb.limit());
        ch.position(ch.position() + n);
        bb.clear(); bb.limit(0);
        pos += r + n;
    }

    static int primSize(int t) {
        if (t == 2) return 8;
        switch (t) { case 4: case 8: return 1; case 5: case 9: return 2;
            case 6: case 10: return 4; case 7: case 11: return 8; default: return 1; }
    }

    /** 默认关键词清单来自 2026-10 iface OOM（openGauss SQLWarning 风暴）实战，按业务/驱动定制。 */
    static final String[] DEFAULT_KEYWORDS = {
        "NOTICE", "WARNING", "ERROR", "PSQL", "SQLException", "FIND_IN_SET",
        "openGauss", "does not exist", "duplicate key", "deadlock", "rollback",
        "transaction", "relation", "permission denied", "timeout", "Connection",
        "SELECT", "INSERT", "UPDATE", "DELETE"
    };
    static String[] KEYWORDS = DEFAULT_KEYWORDS;
    static long[] kwCount;
    static List<List<String>> kwSamples;

    static void initKeywords(String[] kws) {
        KEYWORDS = kws;
        kwCount = new long[kws.length];
        kwSamples = new ArrayList<>();
        for (int i = 0; i < kws.length; i++) kwSamples.add(new ArrayList<>());
    }

    static String[] loadKeywords(String path) throws IOException {
        List<String> l = new ArrayList<>();
        for (String line : Files.readAllLines(Paths.get(path), StandardCharsets.UTF_8)) {
            String s = line.trim();
            if (!s.isEmpty() && !s.startsWith("#")) l.add(s);
        }
        if (l.isEmpty()) throw new IOException("keywords file is empty: " + path);
        return l.toArray(new String[0]);
    }

    static long charArrays = 0, charTotal = 0, shortArrays = 0, intArrays = 0, byteArrays = 0;
    static HashMap<Integer, Long> charLens = new HashMap<>(), shortLens = new HashMap<>(), intLens = new HashMap<>();
    static long shortZero = 0, intZero = 0;
    static int shortSamples = 0, intSamples = 0, byteSamples = 0;
    static boolean sawHeapDump = false;

    public static void main(String[] args) throws Exception {
        if (args.length < 1) {
            System.err.println("Usage: java HprofArrays <heap.hprof> [keywords.txt]");
            System.exit(1);
        }
        initKeywords(args.length > 1 ? loadKeywords(args[1]) : DEFAULT_KEYWORDS);

        Path p = Paths.get(args[0]);
        fileSize = Files.size(p);
        ch = FileChannel.open(p, StandardOpenOption.READ);

        // header
        while (u1() != 0) { }
        u4(); u8();

        char[] cbuf = new char[8192];
        while (pos < fileSize) {
            int tag = u1();
            u4();
            long len = u4();
            long end = pos + len;
            if (tag == 0x0A || tag == 0x1C || tag == 0x0C) { // HEAP DUMP (1.0.1 single 0x0C / 1.0.2 segment 0x1C)
                sawHeapDump = true;
                while (pos < end) {
                    int st = u1();
                    switch (st) {
                        case 0x21: { // instance
                            u8(); u4(); u8();
                            long flen = u4();
                            skip(flen);
                            break;
                        }
                        case 0x22: { // object array
                            u8(); u4();
                            long n = u4();
                            u8();
                            skip(n * 8);
                            break;
                        }
                        case 0x23: { // primitive array
                            u8(); u4();
                            long n = u4();
                            int et = u1();
                            int sz = primSize(et);
                            if (et == 5) { // char[]
                                charArrays++; charTotal += n;
                                charLens.merge((int) Math.min(n, 1_000_000), 1L, Long::sum);
                                int take = (int) Math.min(n, cbuf.length);
                                need(take * 2);
                                for (int i = 0; i < take; i++) cbuf[i] = (char) u2();
                                scanChars(cbuf, take);
                                skip((n - take) * 2L);
                            } else if (et == 9) { // short[]
                                shortArrays++;
                                shortLens.merge((int) Math.min(n, 1_000_000), 1L, Long::sum);
                                int take = (int) Math.min(n, 32);
                                need(take * 2);
                                short[] v = new short[take];
                                boolean zero = true;
                                for (int i = 0; i < take; i++) { v[i] = (short) u2(); if (v[i] != 0) zero = false; }
                                if (zero && n == take) shortZero++;
                                if (shortSamples < 8) {
                                    shortSamples++;
                                    System.out.println("SHORT len=" + n + " " + Arrays.toString(v));
                                }
                                skip((n - take) * 2L);
                            } else if (et == 10) { // int[]
                                intArrays++;
                                intLens.merge((int) Math.min(n, 1_000_000), 1L, Long::sum);
                                int take = (int) Math.min(n, 32);
                                need(take * 4);
                                int[] v = new int[take];
                                boolean zero = true;
                                for (int i = 0; i < take; i++) { v[i] = (int) u4(); if (v[i] != 0) zero = false; }
                                if (zero && n == take) intZero++;
                                if (intSamples < 8) {
                                    intSamples++;
                                    System.out.println("INT len=" + n + " " + Arrays.toString(v));
                                }
                                skip((n - take) * 4L);
                            } else if (et == 8) { // byte[]
                                byteArrays++;
                                int take = (int) Math.min(n, 256);
                                need(take);
                                byte[] b = new byte[take];
                                bb.get(b); pos += take;
                                if (byteSamples < 5) {
                                    byteSamples++;
                                    String s = new String(b, StandardCharsets.ISO_8859_1).replaceAll("[^\\x20-\\x7e]", ".");
                                    System.out.println("BYTE len=" + n + " " + s);
                                }
                                skip(n - take);
                            } else {
                                skip(n * sz);
                            }
                            break;
                        }
                        case 0x20: { // class dump
                            u8(); u4(); skip(48);
                            u4();
                            int cp = u2();
                            for (int i = 0; i < cp; i++) { skip(2); int t = u1(); skip(primSize(t)); }
                            int sc = u2();
                            for (int i = 0; i < sc; i++) { skip(8); int t = u1(); skip(primSize(t)); }
                            int ic = u2();
                            skip(ic * 9L);
                            break;
                        }
                        case 0xFF: case 0x05: case 0x07:
                        case 0x89: case 0x8A: case 0x8B: case 0x8C: case 0x8D:
                        case 0x90: skip(8); break;
                        case 0x01: case 0x02: case 0x03: case 0x08: case 0x8E: skip(16); break;
                        case 0x04: case 0x06: skip(12); break;
                        case 0xFE: skip(12); break;
                        case 0xC3: { // prim array no data
                            u8(); u4();
                            long n = u4();
                            int et = u1();
                            if (et == 5) { charArrays++; charTotal += n; charLens.merge((int) Math.min(n, 1_000_000), 1L, Long::sum); }
                            else if (et == 9) { shortArrays++; shortLens.merge((int) Math.min(n, 1_000_000), 1L, Long::sum); }
                            else if (et == 10) { intArrays++; intLens.merge((int) Math.min(n, 1_000_000), 1L, Long::sum); }
                            else if (et == 8) byteArrays++;
                            break;
                        }
                        default:
                            throw new IOException("unknown subrecord 0x" + Integer.toHexString(st) + " at " + (pos - 1));
                    }
                }
            }
            if (pos > end) throw new IOException("overrun");
            if (pos < end) skip(end - pos);
        }

        if (!sawHeapDump) {
            System.err.println("ERROR: no heap-dump record found (tags 0x0C/0x1C) — "
                    + "unsupported HPROF variant? Refusing to report empty results.");
            System.exit(2);
        }

        System.out.printf("%nchar[] arrays=%,d chars=%,d (%.1f MiB payload)%n", charArrays, charTotal, charTotal * 2.0 / 1048576);
        System.out.printf("short[] arrays=%,d  int[] arrays=%,d  byte[] arrays=%,d%n", shortArrays, intArrays, byteArrays);
        System.out.println("char length top: " + top(charLens));
        System.out.println("short length top: " + top(shortLens));
        System.out.println("int length top: " + top(intLens));
        System.out.println("short zero(first32)=" + shortZero + " int zero(first32)=" + intZero);
        System.out.println("\n=== KEYWORD HITS IN char[] ===");
        for (int i = 0; i < KEYWORDS.length; i++) {
            if (kwCount[i] == 0) continue;
            System.out.println(KEYWORDS[i] + " : " + kwCount[i]);
            for (String s : kwSamples.get(i)) System.out.println("    " + s);
        }
    }

    static String top(HashMap<Integer, Long> m) {
        List<Map.Entry<Integer, Long>> l = new ArrayList<>(m.entrySet());
        l.sort((a, b) -> Long.compare(b.getValue(), a.getValue()));
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < Math.min(8, l.size()); i++)
            sb.append(l.get(i).getKey()).append("->").append(l.get(i).getValue()).append("  ");
        return sb.toString();
    }

    static void scanChars(char[] c, int len) {
        for (int k = 0; k < KEYWORDS.length; k++) {
            if (containsIgnoreCase(c, len, KEYWORDS[k])) {
                kwCount[k]++;
                List<String> list = kwSamples.get(k);
                if (list.size() < 5) {
                    String s = new String(c, 0, Math.min(len, 300)).replaceAll("[\\r\\n\\t]", " ");
                    if (!list.contains(s)) list.add(s);
                }
            }
        }
    }
    static boolean containsIgnoreCase(char[] c, int len, String key) {
        int kl = key.length();
        outer:
        for (int i = 0; i + kl <= len; i++) {
            for (int j = 0; j < kl; j++) {
                char a = c[i + j], b = key.charAt(j);
                if (a != b && Character.toLowerCase(a) != Character.toLowerCase(b)) continue outer;
            }
            return true;
        }
        return false;
    }
}
