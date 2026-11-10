import java.io.*;
import java.nio.ByteBuffer;
import java.nio.channels.FileChannel;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;

/**
 * Streaming HPROF histogram over ALL objects (reachable + unreachable).
 * Zero-dependency, Java 8+; 8MB direct buffer handles multi-GB dumps
 * (verified on a 4.5GB dump where MAT/jhat cannot run).
 *
 * Usage:   java HprofHistogram <heap.hprof> [out.csv]
 * Output:  console TOP-40 by count and by shallow bytes + full CSV histogram.
 *
 * Supported: HPROF 1.0.2 (segmented, tag 0x1C) and 1.0.1 (single 0x0C record),
 * both HotSpot writers; idSize=8 (64-bit JVM). Unknown heap sub-records fail
 * fast — extend the switch if a newer JVM adds one. Refuses to report an empty
 * histogram when no heap-dump record was seen (exit code 2).
 * Sizes are approximations: 16-byte header + declared instance size / element
 * size. Object arrays counted as 16 + n*idSize (v2; v1 under-counted assuming
 * compressed-oop 4-byte refs — do not compare byte columns across versions).
 */
public class HprofHistogram {
    static FileChannel ch;
    static ByteBuffer bb = ByteBuffer.allocateDirect(8 << 20);
    static long pos = 0;
    static long fileSize;
    static int idSize = 8;
    static { bb.limit(0); }

    static void refill() throws IOException {
        bb.compact();
        int n;
        do { n = ch.read(bb); } while (n == 0);
        if (n < 0) throw new EOFException("EOF at " + pos);
        bb.flip();
    }
    static void need(int k) throws IOException {
        if (bb.remaining() < k) refill();
    }
    static int u1() throws IOException { need(1); pos++; return bb.get() & 0xff; }
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
    static String utf8(int len) throws IOException {
        byte[] b = new byte[len];
        int off = 0;
        while (off < len) {
            int r = Math.min(len - off, bb.remaining());
            if (r == 0) { refill(); continue; }
            bb.get(b, off, r);
            off += r;
        }
        pos += len;
        return new String(b, StandardCharsets.UTF_8);
    }

    static final class LongMap {
        long[] keys; long[] vals; int mask; int size;
        LongMap(int cap) {
            int c = 1; while (c < cap) c <<= 1;
            keys = new long[c]; vals = new long[c]; mask = c - 1;
            Arrays.fill(vals, -1L);
        }
        int slot(long k) {
            int i = (int) ((k ^ (k >>> 32)) * 0x9E3779B97F4A7C15L >>> 40) & mask;
            while (keys[i] != 0) {
                if (keys[i] == k) return i;
                i = (i + 1) & mask;
            }
            return -i - 1;
        }
        long get(long k) { int i = slot(k); return i >= 0 ? vals[i] : -1L; }
        void put(long k, long v) {
            int i = slot(k);
            if (i >= 0) { vals[i] = v; return; }
            i = -i - 1; keys[i] = k; vals[i] = v;
            if (++size * 2 > keys.length) rehash();
        }
        void rehash() {
            long[] ok = keys, ov = vals;
            int oc = ok.length;
            keys = new long[oc << 1]; vals = new long[oc << 1]; mask = keys.length - 1;
            Arrays.fill(vals, -1L); size = 0;
            for (int i = 0; i < oc; i++) if (ok[i] != 0) put(ok[i], ov[i]);
        }
    }

    static final int MAXC = 1 << 18;
    static long[] stId = new long[MAXC];
    static long[] stCnt = new long[MAXC];
    static long[] stBytes = new long[MAXC];
    static int stN = 0;
    static LongMap idToStat = new LongMap(1 << 16);
    static LongMap idToSize = new LongMap(1 << 16);
    static LongMap classToNameId = new LongMap(1 << 16);
    static HashMap<Long, String> strings = new HashMap<>(1 << 19);

    static int statFor(long cid) {
        long v = idToStat.get(cid);
        if (v >= 0) return (int) v;
        int idx = stN++;
        stId[idx] = cid;
        idToStat.put(cid, idx);
        return idx;
    }

    static final String[] PRIM = new String[12];
    static {
        PRIM[4] = "[Z (boolean[])"; PRIM[5] = "[C (char[])"; PRIM[6] = "[F (float[])";
        PRIM[7] = "[D (double[])"; PRIM[8] = "[B (byte[])"; PRIM[9] = "[S (short[])";
        PRIM[10] = "[I (int[])"; PRIM[11] = "[J (long[])";
    }
    static int primSize(int t) {
        if (t == 2) return idSize; // object id
        switch (t) { case 4: case 8: return 1; case 5: case 9: return 2;
            case 6: case 10: return 4; case 7: case 11: return 8; default: return 1; }
    }

    static long instances = 0, objArrays = 0, primArrays = 0, unreachableMarks = 0;
    static long totalBytes = 0;
    static boolean sawHeapDump = false;

    public static void main(String[] args) throws Exception {
        if (args.length < 1) {
            System.err.println("Usage: java HprofHistogram <heap.hprof> [out.csv]");
            System.exit(1);
        }
        Path p = Paths.get(args[0]);
        Path csvPath = Paths.get(args.length > 1 ? args[1] : "full_histogram.csv");
        fileSize = Files.size(p);
        ch = FileChannel.open(p, StandardOpenOption.READ);

        StringBuilder magic = new StringBuilder();
        int c;
        while ((c = u1()) != 0) magic.append((char) c);
        idSize = (int) u4();
        long ts = u8();
        System.out.println("magic=" + magic + " idSize=" + idSize + " time=" + new Date(ts));
        System.out.println("fileSize=" + fileSize);

        while (pos < fileSize) {
            int tag = u1();
            long time = u4();
            long len = u4();
            long end = pos + len;
            switch (tag) {
                case 0x01: { // STRING IN UTF8
                    long id = u8();
                    int slen = (int) (len - idSize);
                    strings.put(id, utf8(slen));
                    break;
                }
                case 0x02: { // LOAD CLASS
                    u4();                 // class serial
                    long cid = u8();
                    u4();                 // stack trace serial
                    long nameId = u8();
                    classToNameId.put(cid, nameId);
                    break;
                }
                case 0x0A: case 0x1C: case 0x0C: { // HEAP DUMP (1.0.1 single 0x0C / 1.0.2 segment 0x1C; 0x0A kept for safety)
                    sawHeapDump = true;
                    while (pos < end) {
                        int st = u1();
                        switch (st) {
                            case 0x21: { // INSTANCE
                                u8(); u4();
                                long cid = u8();
                                long flen = u4();
                                int idx = statFor(cid);
                                long sz = idToSize.get(cid);
                                if (sz < 0) sz = 16 + flen;
                                stCnt[idx]++; stBytes[idx] += sz;
                                instances++; totalBytes += sz;
                                skip(flen);
                                break;
                            }
                            case 0x22: { // OBJECT ARRAY
                                u8(); u4();
                                long n = u4();
                                long cid = u8();
                                int idx = statFor(cid);
                                long sz = 16 + n * idSize;
                                stCnt[idx]++; stBytes[idx] += sz;
                                objArrays++; totalBytes += sz;
                                skip(n * idSize);
                                break;
                            }
                            case 0x23: { // PRIMITIVE ARRAY
                                u8(); u4();
                                long n = u4();
                                int et = u1();
                                int idx = statFor(-et);
                                long sz = 16 + n * primSize(et);
                                stCnt[idx]++; stBytes[idx] += sz;
                                primArrays++; totalBytes += sz;
                                skip(n * primSize(et));
                                break;
                            }
                            case 0xC3: { // PRIMITIVE ARRAY, NO DATA
                                u8(); u4();
                                long n = u4();
                                int et = u1();
                                int idx = statFor(-et);
                                long sz = 16 + n * primSize(et);
                                stCnt[idx]++; stBytes[idx] += sz;
                                primArrays++; totalBytes += sz;
                                break;
                            }
                            case 0x20: { // CLASS DUMP
                                long cid = u8();
                                u4();
                                skip(8 * 6); // super, loader, signers, protection, 2 reserved
                                long instSize = u4();
                                idToSize.put(cid, instSize);
                                int cp = (int) (u1() << 8 | u1()); // u2 big-endian
                                for (int i = 0; i < cp; i++) {
                                    skip(2);
                                    int t = u1();
                                    skip(primSize(t));
                                }
                                int sc = (int) (u1() << 8 | u1());
                                for (int i = 0; i < sc; i++) {
                                    skip(8);
                                    int t = u1();
                                    skip(primSize(t));
                                }
                                int ic = (int) (u1() << 8 | u1());
                                skip(ic * 9L);
                                break;
                            }
                            case 0xFF: case 0x05: case 0x07:
                                skip(8); break;
                            case 0x01: case 0x02: case 0x03: case 0x08:
                                skip(16); break;
                            case 0x04: case 0x06:
                                skip(12); break;
                            case 0x89: case 0x8A: case 0x8B: case 0x8C: case 0x8D:
                                skip(8); break;
                            case 0x8E:
                                skip(16); break;
                            case 0x90:
                                skip(8); unreachableMarks++; break;
                            case 0xFE:
                                skip(12); break;
                            default:
                                throw new IOException("unknown heap subrecord 0x" + Integer.toHexString(st)
                                        + " at " + (pos - 1) + " segmentEnd=" + end);
                        }
                    }
                    break;
                }
                default:
                    break;
            }
            if (pos > end) throw new IOException("overrun tag=0x" + Integer.toHexString(tag)
                    + " pos=" + pos + " end=" + end);
            if (pos < end) skip(end - pos);
        }

        if (!sawHeapDump) {
            System.err.println("ERROR: no heap-dump record found (tags 0x0C/0x1C) — "
                    + "unsupported HPROF variant? Refusing to emit an empty histogram.");
            System.exit(2);
        }

        System.out.printf("objects: instances=%,d objArrays=%,d primArrays=%,d total=%,d%n",
                instances, objArrays, primArrays, instances + objArrays + primArrays);
        System.out.printf("approx shallow bytes=%,d (%.1f MiB)%n", totalBytes, totalBytes / 1048576.0);
        System.out.println("classes with objects=" + stN + ", unreachableMarks=" + unreachableMarks);

        Integer[] order = new Integer[stN];
        for (int i = 0; i < stN; i++) order[i] = i;

        System.out.println("\n=== TOP 40 BY OBJECT COUNT (ALL OBJECTS, INCL. UNREACHABLE) ===");
        Arrays.sort(order, (a, b) -> Long.compare(stCnt[b], stCnt[a]));
        for (int i = 0; i < Math.min(40, stN); i++) {
            int k = order[i];
            System.out.printf("%12d  %10.1f MiB  %s%n", stCnt[k], stBytes[k] / 1048576.0, name(stId[k]));
        }

        System.out.println("\n=== TOP 40 BY APPROX SHALLOW BYTES ===");
        Arrays.sort(order, (a, b) -> Long.compare(stBytes[b], stBytes[a]));
        for (int i = 0; i < Math.min(40, stN); i++) {
            int k = order[i];
            System.out.printf("%10.1f MiB  %12d  %s%n", stBytes[k] / 1048576.0, stCnt[k], name(stId[k]));
        }

        try (PrintWriter pw = new PrintWriter(csvPath.toFile(), "UTF-8")) {
            pw.println("class,count,shallow_bytes");
            for (int i = 0; i < stN; i++)
                pw.printf("\"%s\",%d,%d%n", name(stId[i]).replace("\"", "\"\""), stCnt[i], stBytes[i]);
        }
        System.out.println("\nCSV written: " + csvPath);
    }

    static String name(long id) {
        if (id < 0) {
            int t = (int) -id;
            return t >= 0 && t < PRIM.length && PRIM[t] != null ? PRIM[t] : "prim-" + t;
        }
        long nameId = classToNameId.get(id);
        if (nameId >= 0) {
            String s = strings.get(nameId);
            if (s != null) return s;
        }
        return "class@0x" + Long.toHexString(id);
    }
}
