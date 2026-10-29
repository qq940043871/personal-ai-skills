/**
 * store.js 业务自测（Node 环境，用内存对象模拟 wx.storage）
 * 覆盖：签到积分口径 / 成长与进化 / 龙鳞 / 经文 / 领养 / 换宠 / 改名 / 放归 / 比武 / 成员增删改
 */

// ---- 模拟小程序 API ----
const memory = {}
global.wx = {
  getStorageSync(key) {
    return Object.prototype.hasOwnProperty.call(memory, key) ? memory[key] : ''
  },
  setStorageSync(key, value) {
    memory[key] = JSON.parse(JSON.stringify(value))
  }
}

const store = require('../utils/store.js')

let passed = 0
let failed = 0

function check(name, cond, extra) {
  if (cond) {
    passed++
    console.log('  ✓ ' + name)
  } else {
    failed++
    console.log('  ✗ ' + name + (extra !== undefined ? '  → ' + JSON.stringify(extra) : ''))
  }
}

function section(title) {
  console.log('\n' + title)
}

/* ============ 1. 初始数据 ============ */
section('1. 初始数据')
check('5 位家庭成员', store.getMembers().length === 5, store.getMembers().length)
check('爸爸存在', !!store.findMember('dad'))
check('奶奶存在', !!store.findMember('grandma'))

/* ============ 2. 成员初始任务全部为未完成状态用于测试 ============ */
section('2. 家长签到（积分 + 成长）')
const dadBefore = JSON.parse(JSON.stringify(store.findMember('dad')))
const r1 = store.doCheckin('dad', 'd3')
check('签到返回结果', !!r1)
check('任务被标记完成', store.findMember('dad').tasks.find(t => t.id === 'd3').done === true)
check('积分 +15', store.findMember('dad').points === dadBefore.points + 15,
  store.findMember('dad').points)
check('成长 +10', store.findMember('dad').grow === dadBefore.grow + 10, store.findMember('dad').grow)
check('总签到 +1', store.findMember('dad').totalCheckins === dadBefore.totalCheckins + 1)
check('连签 +1', store.findMember('dad').streak === dadBefore.streak + 1)
check('重复签到返回 null', store.doCheckin('dad', 'd3') === null)
check('不存在的任务返回 null', store.doCheckin('dad', 'not-exist') === null)
check('不存在的成员返回 null', store.doCheckin('nobody', 'd1') === null)

/* ============ 3. 幼儿：星星 + 2 倍速 + 进化 ============ */
section('3. 幼儿签到（星星 / 2 倍成长 / 进化）')
const babyBefore = JSON.parse(JSON.stringify(store.findMember('erbao')))
check('幼儿初始阶段为小鸡', store.stageFor(babyBefore).stage === '小鸡', store.stageFor(babyBefore).stage)
const rBaby1 = store.doCheckin('erbao', 'e1')
check('星星 +5', store.findMember('erbao').stars === babyBefore.stars + 5, store.findMember('erbao').stars)
check('成长 +20（2 倍速）', store.findMember('erbao').grow === babyBefore.grow + 20, store.findMember('erbao').grow)
check('第一次未进化', rBaby1.evolved === false, rBaby1.evolved)
const rBaby2 = store.doCheckin('erbao', 'e2')
check('第二次触发进化（小鸡 → 大公鸡）', rBaby2.evolved === true, rBaby2.newStage)
check('进化后阶段为大公鸡', rBaby2.newStage.stage === '大公鸡', rBaby2.newStage.stage)
check('幼儿不用积分口径而用星星', store.scoreLabel(store.findMember('erbao')) === '星星')

/* ============ 4. 奶奶：恩典值 + 经文 ============ */
section('4. 奶奶签到（恩典值 / 经文）')
const gBefore = JSON.parse(JSON.stringify(store.findMember('grandma')))
const rG = store.doCheckin('grandma', 'g4')
check('恩典值 +10', store.findMember('grandma').grace === gBefore.grace + 10, store.findMember('grandma').grace)
check('推送经文', !!rG.verse && !!rG.verse.text, rG.verse)
check('经文带出处', !!rG.verse.ref, rG.verse)
check('奶奶积分口径为恩典值', store.scoreLabel(store.findMember('grandma')) === '恩典值')
check('奶奶签到不加积分', store.findMember('grandma').points === 0)
check('奶奶 stage 使用慢成长体系', store.stageFor(store.findMember('grandma')).stage.indexOf('龟') > -1,
  store.stageFor(store.findMember('grandma')).stage)

/* ============ 5. 9 岁孩子：龙鳞每 5 次一片 ============ */
section('5. 学龄孩子签到（龙鳞）')
const dabao = store.findMember('dabao')
const startScales = dabao.dragonScales
const checkinsBefore = dabao.totalCheckins
// 补到下一次 5 的倍数
let need = 5 - (checkinsBefore % 5)
const undone = dabao.tasks.filter(t => !t.done)
let used = 0
for (let i = 0; i < need && used < undone.length; i++) {
  const res = store.doCheckin('dabao', undone[used].id)
  used++
  if (i === need - 1) {
    check('每 5 次签到获得 1 片龙鳞', store.findMember('dabao').dragonScales === startScales + 1,
      { before: startScales, after: store.findMember('dabao').dragonScales })
    check('签到结果标记获得龙鳞', res && res.scaleGained === true)
  }
}

/* ============ 6. 领养系统 ============ */
section('6. 宠物领养')
const mom = store.findMember('mom')
check('妈妈积分足够', store.scoreValue(mom) === 3250, store.scoreValue(mom))
const adoptable = store.getAdoptablePets('mom')
check('可领养列表非空', adoptable.length > 0, adoptable.length)
check('可领养列表不含默认宠物', adoptable.every(p => !p.defaultFor))
check('可领养列表不含已拥有', adoptable.every(p => !mom.adoptedPets.includes(p.id)))
const highEnd = adoptable.find(p => p.requiredPoints === 3000)
check('包含积分达标的传说宠物（3250 分可领 3000 分档）', !!highEnd, highEnd && highEnd.name)

const catalog = store.getAllCatalogPets('mom')
check('全图鉴含锁定项', catalog.some(p => p.unlocked === false))
check('全图鉴含解锁项', catalog.some(p => p.unlocked === true))

const adoptRes = store.adoptPet('mom', 'lion_fire')
check('领养成功', adoptRes.success === true, adoptRes.msg)
check('领养后计入 adoptedPets', store.findMember('mom').adoptedPets.indexOf('lion_fire') > -1)
check('重复领养被拒绝', store.adoptPet('mom', 'lion_fire').success === false)
check('余额不足的宠物被拒绝', store.adoptPet('mom', 'fox_nine').success === false)
check('默认宠物不可领养', store.adoptPet('mom', 'dad_default').success === false)
check('不存在的宠物被拒绝', store.adoptPet('mom', 'no_such_pet').success === false)

// 幼儿积分少，应领不到高级宠物
const babyAdopt = store.adoptPet('erbao', 'dragon_golden')
check('幼儿领不到神话宠物', babyAdopt.success === false, babyAdopt.msg)

/* ============ 7. 出战 / 改名 / 放归 ============ */
section('7. 出战 / 改名 / 放归')
check('切换出战成功', store.switchActivePet('mom', 'lion_fire') === true)
check('出战宠物已更新', store.findMember('mom').activePetId === 'lion_fire')
check('成员卡宠物名同步为图鉴名', store.findMember('mom').pet.name === '火焰狮',
  store.findMember('mom').pet.name)
const pets = store.getMemberPets('mom')
check('已拥有 2 只宠物', pets.length === 2, pets.length)
check('出战标记正确', pets.find(p => p.id === 'lion_fire').active === true)

const renameRes = store.renamePet('mom', 'lion_fire', '小烈焰')
check('改名成功', renameRes.success === true && renameRes.name === '小烈焰', renameRes)
check('成员卡宠物名同步为自定义名', store.findMember('mom').pet.name === '小烈焰',
  store.findMember('mom').pet.name)
check('改名带稀有度标签', store.getMemberPets('mom').find(p => p.id === 'lion_fire').rarityLabel === '史诗')
const restoreRes = store.renamePet('mom', 'lion_fire', '   ')
check('空名恢复图鉴默认名', restoreRes.name === '火焰狮', restoreRes)

check('放归失败（仅剩 1 只时）', store.releasePet('dad', 'dad_default').success === false)
const releaseRes = store.releasePet('mom', 'mom_default')
check('放归非出战宠物成功', releaseRes.success === true, releaseRes.msg)
check('放归后自动切到剩余宠物', store.findMember('mom').activePetId === 'lion_fire',
  store.findMember('mom').activePetId)
check('放归后宠物数正确', store.getMemberPets('mom').length === 1)

/* ============ 8. 比武 ============ */
section('8. 宠物比武')
const dadM = store.findMember('dad')
const momM = store.findMember('mom')
const battle = store.doBattle(dadM, momM)
check('比武产生结果', !!battle)
check('胜者是其中一方', battle.winner.id === 'dad' || battle.winner.id === 'mom', battle.winner.id)
check('败者是另一方', battle.loser.id !== battle.winner.id)
check('幼儿参战返回 null（平局）', store.doBattle(store.findMember('erbao'), momM) === null)

const winnerBefore = store.scoreValue(battle.winner)
store.rewardBattleWinner(battle.winner.id, 30)
check('胜者积分 +30', store.scoreValue(store.findMember(battle.winner.id)) === winnerBefore + 30,
  { before: winnerBefore, after: store.scoreValue(store.findMember(battle.winner.id)) })

const attrs = store.getPetAttrs(dadM)
check('四维属性齐全', ['strength', 'wisdom', 'vitality', 'charm'].every(k => typeof attrs[k] === 'number'))
check('属性不超过 100', Object.keys(attrs).every(k => attrs[k] <= 100))
check('总战力 = 四维之和', store.getPetTotalPower(dadM) ===
  attrs.strength + attrs.wisdom + attrs.vitality + attrs.charm)
check('null 成员不崩溃', store.getPetAttrs(null).strength === 0)

/* ============ 9. 成员增删改 ============ */
section('9. 成员增删改')
const countBefore = store.getMembers().length
const added = store.addMember({ name: '  测试成员  ', age: 30, petName: '小七' })
check('新增成员成功', store.getMembers().length === countBefore + 1)
check('姓名去空格', added.name === '测试成员', added.name)
check('角色按年龄推导', added.role === '家长', added.role)
check('成长上限按年龄', added.totalGrow === 1000, added.totalGrow)
check('默认任务 3 条', added.tasks.length === 3)
check('默认宠物已命名', added.pet.name === '小七')

const addedBaby = store.addMember({ name: '小测试', age: 2 })
check('幼儿成长上限 100', addedBaby.totalGrow === 100, addedBaby.totalGrow)
check('幼儿角色', addedBaby.role === '幼儿', addedBaby.role)
const addedElder = store.addMember({ name: '老太', age: 70 })
check('长辈成长上限 1600', addedElder.totalGrow === 1600, addedElder.totalGrow)

// 年龄变更应等比换算成长值并切换体系
store.updateMember(addedBaby.id, { age: 40 })
const converted = store.findMember(addedBaby.id)
check('年龄变更后角色重算', converted.role === '家长', converted.role)
check('年龄变更后成长上限切换', converted.totalGrow === 1000, converted.totalGrow)
check('年龄变更成长值等比换算', converted.grow === 0, converted.grow)

store.updateMember(added.id, { name: '改过的名字', petName: '改名宠物' })
check('更新姓名生效', store.findMember(added.id).name === '改过的名字')
check('更新宠物名生效', store.findMember(added.id).pet.name === '改名宠物')
check('更新不存在的成员返回 null', store.updateMember('ghost', { name: 'x' }) === null)

// 删除到只剩 1 位
let guard = 0
while (store.getMembers().length > 1 && guard < 30) {
  store.removeMember(store.getMembers()[store.getMembers().length - 1].id)
  guard++
}
check('可删除到只剩 1 位', store.getMembers().length === 1, store.getMembers().length)
check('最后 1 位不可删除', store.removeMember(store.getMembers()[0].id).success === false)
check('删除不存在的成员失败', store.removeMember('ghost').success === false)

/* ============ 10. 统计与持久化 ============ */
section('10. 统计与持久化')
const stats = store.getFamilyStats()
check('统计包含 totalCheckins', typeof stats.totalCheckins === 'number')
check('统计包含 todayTotal', stats.todayTotal > 0, stats.todayTotal)
check('todayDone 不超过 todayTotal', stats.todayDone <= stats.todayTotal)
check('写入过本地存储', !!memory['family_members_v1'])
// 先调用一次，验证首次访问会落缓存
const verse1 = store.getTodayVerse()
const verse2 = store.getTodayVerse()
check('首次访问写入经文缓存', !!memory['family_verse_v1'])
check('经文缓存带日期与内容',
  !!memory['family_verse_v1'].date && !!memory['family_verse_v1'].verse.text)
check('经文同日保持一致', verse1.text === verse2.text)

store.resetAll()
check('恢复初始数据后为 5 位成员', store.getMembers().length === 5, store.getMembers().length)
check('恢复后爸爸积分回到 2340', store.findMember('dad').points === 2340,
  store.findMember('dad').points)
check('恢复后妈妈只剩默认宠物', store.findMember('mom').adoptedPets.length === 1)
check('跨页意图传递', (function () {
  store.setPendingPetMember('grandma')
  return store.consumePendingPetMember() === 'grandma' && store.consumePendingPetMember() === ''
})())

/* ============ 汇总 ============ */
console.log('\n========================================')
console.log('通过 %d 项，失败 %d 项', passed, failed)
console.log('========================================')
process.exit(failed === 0 ? 0 : 1)
