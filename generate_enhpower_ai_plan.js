const PptxGenJS = require('pptxgenjs');

const pptx = new PptxGenJS();
pptx.layout = 'LAYOUT_WIDE';
pptx.author = 'OpenAI Codex';
pptx.company = '佛山市益帕瓦物联科技有限公司';
pptx.subject = 'AI智能体研发规划';
pptx.title = '益帕瓦智慧能源业务AI智能体研发规划';
pptx.lang = 'zh-CN';
pptx.theme = {
  headFontFace: 'Microsoft YaHei',
  bodyFontFace: 'Microsoft YaHei',
  lang: 'zh-CN'
};
pptx.defineLayout({ name: 'ENH', width: 13.333, height: 7.5 });
pptx.layout = 'ENH';

const C = {
  navy: '081A33',
  blue: '0B57D0',
  cyan: '1FB6FF',
  teal: '00C2A8',
  light: 'EAF4FF',
  sky: 'D7EAFE',
  line: '6FA8FF',
  text: '0F172A',
  muted: '5B6B84',
  white: 'FFFFFF',
  slate: 'EEF4FB',
  soft: 'F7FAFE',
  accent: 'FFB84D'
};

const IMG = {
  logo: 'assets/raw/logo.png',
  about: 'assets/raw/about_main.jpg',
  banner: 'assets/raw/product_banner.png',
  fault: 'assets/raw/prod_fault.png',
  planning: 'assets/raw/prod_planning.png',
  renewable: 'assets/raw/prod_renewable.png',
  grid: 'assets/converted/service_grid.png'
};

function addBg(slide, color = C.soft) {
  slide.background = { color };
  slide.addShape(pptx.ShapeType.rect, { x: 0, y: 0, w: 13.333, h: 0.14, line: { color: C.blue, transparency: 100 }, fill: { color: C.blue } });
  slide.addShape(pptx.ShapeType.rect, { x: 0, y: 7.36, w: 13.333, h: 0.14, line: { color: C.navy, transparency: 100 }, fill: { color: C.navy } });
}

function addHeader(slide, title, subtitle) {
  slide.addText(title, {
    x: 0.65, y: 0.38, w: 7.9, h: 0.42,
    fontFace: 'Microsoft YaHei', fontSize: 24, bold: true, color: C.text,
    margin: 0
  });
  if (subtitle) {
    slide.addText(subtitle, {
      x: 0.68, y: 0.83, w: 8.8, h: 0.24,
      fontFace: 'Microsoft YaHei', fontSize: 9.5, color: C.muted,
      margin: 0
    });
  }
  slide.addShape(pptx.ShapeType.line, { x: 0.65, y: 1.13, w: 2.15, h: 0, line: { color: C.blue, pt: 1.5 } });
}

function addFooter(slide, page) {
  slide.addText(`资料来源：公司官网公开信息整理 | AI研发负责人视角 | ${page}`, {
    x: 0.68, y: 7.08, w: 6.2, h: 0.16,
    fontFace: 'Microsoft YaHei', fontSize: 7.5, color: '6B7280',
    margin: 0
  });
}

function addLogoTag(slide) {
  slide.addImage({ path: IMG.logo, x: 11.2, y: 0.34, w: 1.45, h: 0.38 });
}

function addBulletList(slide, items, opts = {}) {
  const x = opts.x ?? 0.9;
  const y = opts.y ?? 1.45;
  const w = opts.w ?? 5.5;
  const h = opts.h ?? 4.8;
  const fontSize = opts.fontSize ?? 16;
  const color = opts.color ?? C.text;
  const bulletIndent = opts.bulletIndent ?? 14;
  const hanging = opts.hanging ?? 3;
  const paragraphSpaceAfterPt = opts.spaceAfterPt ?? 9;
  const text = [];
  items.forEach((item, idx) => {
    text.push({
      text: item,
      options: {
        breakLine: idx !== items.length - 1,
        bullet: { indent: bulletIndent },
        hanging,
        paraSpaceAfterPt: paragraphSpaceAfterPt
      }
    });
  });
  slide.addText(text, {
    x, y, w, h,
    fontFace: 'Microsoft YaHei', fontSize, color,
    margin: 0.03,
    valign: 'top'
  });
}

function card(slide, { x, y, w, h, title, body, fill = C.white, titleColor = C.text, bodyColor = C.muted, accent = C.blue, radius = 0.14 }) {
  slide.addShape(pptx.ShapeType.roundRect, {
    x, y, w, h,
    rectRadius: radius,
    fill: { color: fill },
    line: { color: accent, transparency: 78, pt: 1 }
  });
  slide.addShape(pptx.ShapeType.rect, {
    x: x + 0.02, y: y + 0.02, w: 0.08, h: h - 0.04,
    line: { color: accent, transparency: 100 },
    fill: { color: accent }
  });
  slide.addText(title, {
    x: x + 0.22, y: y + 0.18, w: w - 0.34, h: 0.35,
    fontFace: 'Microsoft YaHei', fontSize: 15, bold: true, color: titleColor,
    margin: 0
  });
  slide.addText(body, {
    x: x + 0.22, y: y + 0.58, w: w - 0.34, h: h - 0.72,
    fontFace: 'Microsoft YaHei', fontSize: 10.5, color: bodyColor,
    margin: 0,
    valign: 'top'
  });
}

function pill(slide, x, y, w, text, fill = C.light, color = C.blue) {
  slide.addShape(pptx.ShapeType.roundRect, {
    x, y, w, h: 0.34,
    rectRadius: 0.1,
    line: { color: fill, transparency: 100 },
    fill: { color: fill }
  });
  slide.addText(text, {
    x, y: y + 0.04, w, h: 0.18,
    fontFace: 'Microsoft YaHei', fontSize: 9.5, bold: true, color,
    align: 'center', margin: 0
  });
}

function sectionBar(slide, x, y, w, text) {
  slide.addShape(pptx.ShapeType.roundRect, {
    x, y, w, h: 0.36,
    rectRadius: 0.08,
    line: { color: C.blue, transparency: 100 },
    fill: { color: C.blue }
  });
  slide.addText(text, {
    x: x + 0.14, y: y + 0.06, w: w - 0.28, h: 0.18,
    fontFace: 'Microsoft YaHei', fontSize: 10.5, bold: true, color: C.white,
    margin: 0
  });
}

function addScenarioTile(slide, x, y, w, h, title, points, accent, tag) {
  slide.addShape(pptx.ShapeType.roundRect, {
    x, y, w, h,
    rectRadius: 0.12,
    fill: { color: C.white },
    line: { color: accent, transparency: 55, pt: 1.1 }
  });
  slide.addShape(pptx.ShapeType.rect, {
    x, y, w: w, h: 0.07,
    line: { color: accent, transparency: 100 },
    fill: { color: accent }
  });
  slide.addText(title, {
    x: x + 0.18, y: y + 0.18, w: w - 0.36, h: 0.24,
    fontFace: 'Microsoft YaHei', fontSize: 12.5, bold: true, color: C.text,
    margin: 0
  });
  if (tag) pill(slide, x + w - 1.25, y + 0.14, 0.98, tag, C.light, accent);
  addBulletList(slide, points, { x: x + 0.16, y: y + 0.56, w: w - 0.28, h: h - 0.68, fontSize: 9.2, bulletIndent: 10, hanging: 2.5, spaceAfterPt: 5 });
}

function drawArchitecture(slide) {
  const layers = [
    { y: 1.5, h: 0.72, title: '业务入口层', items: ['调度/运维驾驶舱', '预测与规划系统', '故障研判台', '智慧能源运营门户'], fill: 'E9F5FF', accent: C.cyan },
    { y: 2.45, h: 0.9, title: '智能体编排层', items: ['调度优化智能体', '负荷预测智能体', '新能源预测智能体', '故障诊断智能体', '规划设计智能体'], fill: 'EAFBF7', accent: C.teal },
    { y: 3.62, h: 1.05, title: '模型与决策引擎层', items: ['大模型/RAG', '图谱与规则库', '时序预测模型', '优化求解器', '仿真校核与评测'], fill: 'F0F4FF', accent: C.blue },
    { y: 4.95, h: 1.05, title: '数据与知识层', items: ['SCADA/EMS/DMS/AMI', 'GIS/设备台账/告警工单', '气象/新能源/负荷数据', '规程标准/专家案例/项目文档'], fill: 'F8FAFC', accent: '5B6B84' }
  ];

  layers.forEach(layer => {
    slide.addShape(pptx.ShapeType.roundRect, {
      x: 0.82, y: layer.y, w: 11.7, h: layer.h,
      rectRadius: 0.12,
      fill: { color: layer.fill },
      line: { color: layer.accent, transparency: 45, pt: 1 }
    });
    slide.addText(layer.title, {
      x: 1.02, y: layer.y + 0.18, w: 1.55, h: 0.24,
      fontFace: 'Microsoft YaHei', fontSize: 12, bold: true, color: C.text,
      margin: 0
    });
    const itemW = 1.9;
    const gap = 0.16;
    layer.items.forEach((item, idx) => {
      slide.addShape(pptx.ShapeType.roundRect, {
        x: 2.6 + idx * (itemW + gap), y: layer.y + 0.15, w: itemW, h: layer.h - 0.3,
        rectRadius: 0.08,
        fill: { color: C.white },
        line: { color: layer.accent, transparency: 60, pt: 0.8 }
      });
      slide.addText(item, {
        x: 2.72 + idx * (itemW + gap), y: layer.y + 0.28, w: itemW - 0.24, h: layer.h - 0.56,
        fontFace: 'Microsoft YaHei', fontSize: 9.4, bold: layer.title === '智能体编排层', color: C.text,
        align: 'center', valign: 'mid', margin: 0.03
      });
    });
  });

  [2.24, 3.41, 4.74].forEach(y => {
    slide.addShape(pptx.ShapeType.chevron, {
      x: 6.43, y, w: 0.44, h: 0.22,
      line: { color: C.blue, transparency: 100 },
      fill: { color: C.blue }
    });
  });
}

function addThreeImageStrip(slide) {
  slide.addImage({ path: IMG.fault, x: 8.85, y: 1.76, w: 1.2, h: 0.88 });
  slide.addImage({ path: IMG.planning, x: 10.12, y: 1.76, w: 1.2, h: 0.88 });
  slide.addImage({ path: IMG.renewable, x: 11.39, y: 1.76, w: 1.2, h: 0.88 });
  ['故障诊断', '智能规划', '功率预测'].forEach((label, idx) => {
    slide.addText(label, {
      x: 8.92 + idx * 1.27, y: 2.68, w: 1.06, h: 0.18,
      fontFace: 'Microsoft YaHei', fontSize: 8.5, color: C.muted,
      align: 'center', margin: 0
    });
  });
}

// Slide 1
{
  const slide = pptx.addSlide();
  slide.background = { color: C.navy };
  slide.addImage({ path: IMG.grid, x: 0, y: 0, w: 13.333, h: 7.5 });
  slide.addShape(pptx.ShapeType.rect, { x: 0, y: 0, w: 13.333, h: 7.5, line: { color: C.navy, transparency: 100 }, fill: { color: C.navy, transparency: 38 } });
  slide.addShape(pptx.ShapeType.rect, { x: 0, y: 0, w: 7.2, h: 7.5, line: { color: C.navy, transparency: 100 }, fill: { color: '051123', transparency: 10 } });
  slide.addImage({ path: IMG.logo, x: 0.85, y: 0.62, w: 2.2, h: 0.58 });
  slide.addText('益帕瓦智慧能源业务\nAI智能体研发规划', {
    x: 0.9, y: 1.68, w: 5.8, h: 1.45,
    fontFace: 'Microsoft YaHei', fontSize: 24, bold: true, color: C.white,
    breakLine: true, margin: 0
  });
  slide.addText('以电网技术为核心，构建“咨询 + 算法 + 软件 + 智能体”一体化产品竞争力', {
    x: 0.94, y: 3.26, w: 5.7, h: 0.45,
    fontFace: 'Microsoft YaHei', fontSize: 12.5, color: 'DCEBFF',
    margin: 0
  });
  pill(slide, 0.95, 4.02, 1.58, 'AI研发负责人视角', '153A75', C.white);
  pill(slide, 2.67, 4.02, 1.42, '电网技术融合', '153A75', C.white);
  pill(slide, 4.22, 4.02, 1.55, '智慧能源升级', '153A75', C.white);
  slide.addText('基于官网公开业务方向整理\n2026年3月', {
    x: 0.95, y: 5.68, w: 2.8, h: 0.55,
    fontFace: 'Microsoft YaHei', fontSize: 10.5, color: 'D4DFF3',
    margin: 0
  });
  slide.addShape(pptx.ShapeType.line, { x: 0.95, y: 5.32, w: 1.8, h: 0, line: { color: C.cyan, pt: 1.4 } });
  slide.addText('让电力更智慧，让负荷更智能', {
    x: 8.65, y: 6.55, w: 3.75, h: 0.22,
    fontFace: 'Microsoft YaHei', fontSize: 10, bold: true, color: C.white,
    align: 'right', margin: 0
  });
}

// Slide 2
{
  const slide = pptx.addSlide();
  addBg(slide);
  addHeader(slide, '现有业务基础已经具备 AI 智能体化条件', '官网公开信息显示，公司在咨询、算法、产品三端已经形成较完整的智能化基础。');
  addLogoTag(slide);

  slide.addImage({ path: IMG.about, x: 7.95, y: 1.42, w: 4.7, h: 2.65 });
  slide.addShape(pptx.ShapeType.rect, { x: 7.95, y: 1.42, w: 4.7, h: 2.65, line: { color: C.navy, transparency: 100 }, fill: { color: C.navy, transparency: 68 } });
  slide.addText('“一个助力电力系统智能化的人工智能公司”', {
    x: 8.28, y: 1.74, w: 3.9, h: 0.45,
    fontFace: 'Microsoft YaHei', fontSize: 15, bold: true, color: C.white,
    margin: 0
  });
  slide.addText('使命：让电力更智慧，让负荷更智能\n团队来源：华南理工、天津大学、华北电力、复旦、武汉大学等高校专家与工程师', {
    x: 8.28, y: 2.3, w: 3.98, h: 0.96,
    fontFace: 'Microsoft YaHei', fontSize: 10.5, color: 'E9F2FF',
    margin: 0
  });

  addBulletList(slide, [
    '服务基础：智能电网咨询、高性能计算、调度运行优化决策、电力市场与电网规划咨询。',
    '算法基础：电网运行优化算法引擎、数十种场景算法模型库、深度学习预测偏差自校正。',
    '产品基础：Argri配电网智能故障诊断系统、配电网智能规划系统、新能源功率预测系统。',
    '组织基因：以“电力 + AI + 工业软件”路线切入，适合进一步平台化、产品化、智能体化。'
  ], { x: 0.82, y: 1.48, w: 6.65, h: 2.65, fontSize: 15, bulletIndent: 13, hanging: 3.2, spaceAfterPt: 9 });

  card(slide, { x: 0.82, y: 4.45, w: 3.88, h: 1.7, title: '咨询 Know-how', body: '沉淀调度优化、系统分析、规划咨询等专业方法论，可转化为专家规则、案例库与标准作业流。', accent: C.blue });
  card(slide, { x: 4.82, y: 4.45, w: 3.88, h: 1.7, title: '算法 Know-how', body: '具备预测、诊断、优化求解与数据校核能力，可作为智能体的核心决策与仿真引擎。', accent: C.teal });
  card(slide, { x: 8.82, y: 4.45, w: 3.88, h: 1.7, title: '产品 Know-how', body: '现有故障诊断、规划、功率预测产品可直接升级为“助手化 + 自动化 + 闭环化”的AI产品矩阵。', accent: C.cyan });

  addFooter(slide, '02');
}

// Slide 3
{
  const slide = pptx.addSlide();
  addBg(slide);
  addHeader(slide, '新型电力系统进入“规则 + 模型 + 智能体”协同阶段', '作为AI研发负责人，我的判断是：现在是将公司业务从“项目型智能化”升级到“平台型智能化”的关键窗口。');
  addLogoTag(slide);

  sectionBar(slide, 0.82, 1.45, 2.18, '行业变化');
  card(slide, { x: 0.82, y: 1.88, w: 2.82, h: 1.2, title: '源网荷储协同复杂度上升', body: '新能源波动、负荷侧互动、市场化机制共同抬高实时决策难度。', accent: C.blue });
  card(slide, { x: 3.82, y: 1.88, w: 2.82, h: 1.2, title: '现场知识高度分散', body: '调控经验、规程标准、项目文档和专家判断尚未形成统一知识资产。', accent: C.cyan });
  card(slide, { x: 6.82, y: 1.88, w: 2.82, h: 1.2, title: '多系统协同效率不足', body: '预测、诊断、优化、运维之间仍然依赖人工切换与串联分析。', accent: C.teal });
  card(slide, { x: 9.82, y: 1.88, w: 2.7, h: 1.2, title: '客户期待更强交付', body: '客户不只需要模型结果，更需要可解释、可执行、可闭环的智能助手。', accent: C.accent });

  sectionBar(slide, 0.82, 3.42, 2.18, 'AI机会');
  slide.addShape(pptx.ShapeType.chevron, { x: 1.16, y: 4.22, w: 1.38, h: 0.5, line: { color: C.blue, transparency: 100 }, fill: { color: 'DCEBFF' } });
  slide.addShape(pptx.ShapeType.chevron, { x: 2.58, y: 4.22, w: 1.38, h: 0.5, line: { color: C.blue, transparency: 100 }, fill: { color: 'C9E3FF' } });
  slide.addShape(pptx.ShapeType.chevron, { x: 4.00, y: 4.22, w: 1.38, h: 0.5, line: { color: C.blue, transparency: 100 }, fill: { color: 'B8DAFF' } });
  slide.addText('工具型AI', { x: 1.34, y: 4.37, w: 0.82, h: 0.16, fontFace: 'Microsoft YaHei', fontSize: 10.5, bold: true, color: C.text, align: 'center', margin: 0 });
  slide.addText('Copilot', { x: 2.82, y: 4.37, w: 0.82, h: 0.16, fontFace: 'Microsoft YaHei', fontSize: 10.5, bold: true, color: C.text, align: 'center', margin: 0 });
  slide.addText('Agent', { x: 4.26, y: 4.37, w: 0.82, h: 0.16, fontFace: 'Microsoft YaHei', fontSize: 10.5, bold: true, color: C.text, align: 'center', margin: 0 });
  slide.addText('从问答辅助，升级为可理解任务、调用模型、执行流程、输出建议并进入闭环的智能操作系统。', {
    x: 0.98, y: 4.88, w: 4.78, h: 0.5,
    fontFace: 'Microsoft YaHei', fontSize: 11, color: C.muted, margin: 0
  });

  card(slide, { x: 6.4, y: 3.74, w: 2.82, h: 2.1, title: '对益帕瓦的意义', body: '把高端咨询经验沉淀为可复用资产，把算法能力升级为持续在线的智能服务，把产品能力扩展到客户运行现场。', accent: C.blue });
  card(slide, { x: 9.48, y: 3.74, w: 2.98, h: 2.1, title: '研发策略', body: '优先围绕故障诊断、预测、规划、调度四类现有能力做智能体增强，再向多智能体协同平台演进。', accent: C.teal });

  addFooter(slide, '03');
}

// Slide 4
{
  const slide = pptx.addSlide();
  addBg(slide);
  addHeader(slide, '建议建设公司级 Power Agent 平台架构', '目标不是单点做一个聊天窗口，而是构建贯穿数据、模型、流程、产品的电力智能体底座。');
  addLogoTag(slide);
  drawArchitecture(slide);
  slide.addText('核心原则：强行业知识、强模型协同、强规则约束、强人机共驾、强项目复用。', {
    x: 0.88, y: 6.38, w: 7.8, h: 0.22,
    fontFace: 'Microsoft YaHei', fontSize: 10.5, color: C.muted, margin: 0
  });
  addThreeImageStrip(slide);
  slide.addText('现有产品能力可直接作为智能体编排层的首批“工具插件”与“场景执行器”。', {
    x: 8.85, y: 3.0, w: 3.75, h: 0.42,
    fontFace: 'Microsoft YaHei', fontSize: 11, color: C.text, bold: true, margin: 0
  });
  addBulletList(slide, [
    '故障诊断系统：支持告警理解、原因定位、处置建议。',
    '智能规划系统：支持方案比选、约束校核、报告草拟。',
    '功率预测系统：支持多时尺度预测与偏差修正。'
  ], { x: 8.86, y: 3.48, w: 3.6, h: 1.6, fontSize: 10.2, bulletIndent: 10, hanging: 2.5, spaceAfterPt: 5 });
  addFooter(slide, '04');
}

// Slide 5
{
  const slide = pptx.addSlide();
  addBg(slide);
  addHeader(slide, '重点融合应用场景：先从 6 个高价值场景切入', '围绕官网既有产品和智慧能源方向，我建议从“短期可交付 + 中期可平台化”的场景开始。');
  addLogoTag(slide);

  addScenarioTile(slide, 0.82, 1.52, 3.96, 1.54, '1. 调度优化智能体', ['读取运行边界、检索规则与案例；', '形成调度建议和校核说明；', '服务电网运行优化与咨询项目。'], C.blue, '咨询升级');
  addScenarioTile(slide, 4.92, 1.52, 3.96, 1.54, '2. 负荷预测智能体', ['融合天气、节假日、电价与负荷成分；', '自动解释偏差来源；', '支撑聚合负荷与售电运营。'], C.teal, '算法沉淀');
  addScenarioTile(slide, 9.02, 1.52, 3.5, 1.54, '3. 新能源功率预测智能体', ['接入气象与历史功率；', '输出多时尺度预测与置信区间；', '作为现有产品的智能增强层。'], C.cyan, '现有产品');

  addScenarioTile(slide, 0.82, 3.36, 3.96, 1.54, '4. 配电网故障诊断智能体', ['解析告警和拓扑信息；', '自动给出故障位置、原因与处置建议；', '提升定位速度与现场支撑效率。'], C.accent, 'Argri');
  addScenarioTile(slide, 4.92, 3.36, 3.96, 1.54, '5. 配电网智能规划智能体', ['辅助生成规划假设、方案比选、投资优先级；', '自动形成方案摘要与论证报告。'], C.blue, '现有产品');
  addScenarioTile(slide, 9.02, 3.36, 3.5, 1.54, '6. 源网荷储协同运营智能体', ['面向园区/综合能源场景；', '联动预测、交易、设备控制与运行策略；', '形成智慧能源新增长点。'], C.teal, '智慧能源');

  slide.addImage({ path: IMG.banner, x: 8.72, y: 5.28, w: 3.95, h: 1.32 });
  slide.addShape(pptx.ShapeType.rect, { x: 8.72, y: 5.28, w: 3.95, h: 1.32, line: { color: C.navy, transparency: 100 }, fill: { color: C.navy, transparency: 74 } });
  slide.addText('建议优先级：故障诊断 / 功率预测 / 规划设计先产品化，调度优化与源网荷储作为平台牵引场景。', {
    x: 0.86, y: 5.45, w: 7.25, h: 0.48,
    fontFace: 'Microsoft YaHei', fontSize: 12.5, bold: true, color: C.text, margin: 0
  });
  slide.addText('这样既能快速形成标杆，也能逐步沉淀统一平台。', {
    x: 0.86, y: 6.02, w: 6.6, h: 0.22,
    fontFace: 'Microsoft YaHei', fontSize: 10.5, color: C.muted, margin: 0
  });
  addFooter(slide, '05');
}

// Slide 6
{
  const slide = pptx.addSlide();
  addBg(slide);
  addHeader(slide, '24个月研发路线图：先做可用，再做可复用，最后做可规模化', '研发节奏上，建议采用“三阶段推进”，兼顾项目落地和平台沉淀。');
  addLogoTag(slide);

  const phases = [
    {
      x: 0.9, color: C.blue, title: '阶段一 0-6个月', subtitle: '底座建设与场景验证', bullets: [
        '搭建电力知识库、案例库、规程库与评测集。',
        '完成故障诊断/功率预测两个场景的Agent PoC。',
        '打通权限、安全、日志、反馈闭环机制。',
        '形成第一版AI助手嵌入式交互。'
      ]
    },
    {
      x: 4.45, color: C.teal, title: '阶段二 6-12个月', subtitle: '产品增强与项目复制', bullets: [
        '把故障诊断、规划、预测产品升级为智能助手版。',
        '形成统一工具调用框架和多模型协同机制。',
        '在2-3个标杆项目中完成现场验证。',
        '建立指标体系：准确率、闭环率、节省工时。'
      ]
    },
    {
      x: 8.0, color: C.cyan, title: '阶段三 12-24个月', subtitle: '多智能体协同与商业化', bullets: [
        '建设源网荷储协同运营驾驶舱。',
        '推动调度、规划、预测、运维多智能体协同。',
        '形成平台许可 + 行业解决方案双轮模式。',
        '沉淀可复制的行业模板和伙伴生态。'
      ]
    }
  ];

  phases.forEach(phase => {
    slide.addShape(pptx.ShapeType.roundRect, {
      x: phase.x, y: 1.7, w: 3.1, h: 4.7,
      rectRadius: 0.12,
      fill: { color: C.white },
      line: { color: phase.color, transparency: 30, pt: 1.2 }
    });
    slide.addShape(pptx.ShapeType.rect, {
      x: phase.x, y: 1.7, w: 3.1, h: 0.12,
      line: { color: phase.color, transparency: 100 },
      fill: { color: phase.color }
    });
    slide.addText(phase.title, {
      x: phase.x + 0.2, y: 1.98, w: 2.5, h: 0.22,
      fontFace: 'Microsoft YaHei', fontSize: 14, bold: true, color: C.text,
      margin: 0
    });
    slide.addText(phase.subtitle, {
      x: phase.x + 0.2, y: 2.28, w: 2.5, h: 0.18,
      fontFace: 'Microsoft YaHei', fontSize: 9.8, color: phase.color,
      bold: true, margin: 0
    });
    addBulletList(slide, phase.bullets, { x: phase.x + 0.16, y: 2.7, w: 2.76, h: 2.68, fontSize: 10.3, bulletIndent: 10, hanging: 2.5, spaceAfterPt: 6 });
    pill(slide, phase.x + 0.18, 5.88, 1.75, '关键产出', phase.color, C.white);
    slide.addText(
      phase.title.includes('一') ? '知识库 / 评测集 / 首批PoC' : phase.title.includes('二') ? 'Agent化产品 / 标杆项目' : '平台化方案 / 商业化模板',
      { x: phase.x + 0.24, y: 6.11, w: 2.5, h: 0.18, fontFace: 'Microsoft YaHei', fontSize: 9.6, color: C.muted, margin: 0 }
    );
  });

  slide.addShape(pptx.ShapeType.chevron, { x: 4.02, y: 3.84, w: 0.22, h: 0.38, line: { color: C.blue, transparency: 100 }, fill: { color: C.blue } });
  slide.addShape(pptx.ShapeType.chevron, { x: 7.57, y: 3.84, w: 0.22, h: 0.38, line: { color: C.blue, transparency: 100 }, fill: { color: C.blue } });
  addFooter(slide, '06');
}

// Slide 7
{
  const slide = pptx.addSlide();
  addBg(slide);
  addHeader(slide, '对公司产品竞争力的直接提升', 'AI智能体不是附加功能，而是把公司现有能力重新组织为更高附加值产品的方式。');
  addLogoTag(slide);

  card(slide, { x: 0.82, y: 1.58, w: 3.0, h: 1.45, title: '从“项目交付”到“可复用平台”', body: '把专家方法论、规则和案例沉淀为统一知识资产，减少重复建设。', accent: C.blue });
  card(slide, { x: 4.02, y: 1.58, w: 3.0, h: 1.45, title: '从“单点算法”到“闭环助手”', body: '让预测、诊断、规划结果具备解释、建议、回写和持续学习能力。', accent: C.teal });
  card(slide, { x: 7.22, y: 1.58, w: 2.94, h: 1.45, title: '从“人工支持”到“在线服务”', body: '提升售前演示、项目运维、问题分析和客户陪伴效率。', accent: C.cyan });
  card(slide, { x: 10.36, y: 1.58, w: 2.3, h: 1.45, title: '从“产品”到“产品矩阵”', body: '形成咨询 + 软件 + Agent服务的组合打法。', accent: C.accent });

  sectionBar(slide, 0.82, 3.45, 2.12, '目标指标');
  card(slide, { x: 0.82, y: 3.88, w: 2.8, h: 1.82, title: '+50%', body: '方案编制与技术分析效率提升目标\n通过知识复用和自动草拟减少重复劳动。', accent: C.blue, titleColor: C.blue });
  card(slide, { x: 3.78, y: 3.88, w: 2.8, h: 1.82, title: '3-5x', body: '故障研判与辅助分析速度提升目标\n让一线支持更快形成结论。', accent: C.teal, titleColor: C.teal });
  card(slide, { x: 6.74, y: 3.88, w: 2.8, h: 1.82, title: '-40%', body: '演示与试点交付周期压缩目标\n以Agent演示替代大量定制化沟通。', accent: C.cyan, titleColor: C.cyan });
  card(slide, { x: 9.7, y: 3.88, w: 2.96, h: 1.82, title: '双轮增长', body: '平台许可收入 + 解决方案收入\n形成更稳定的续费与拓展空间。', accent: C.accent, titleColor: C.accent });

  slide.addText('以上为内部目标值，建议在标杆项目中逐步固化为可量化商业案例。', {
    x: 0.86, y: 6.18, w: 6.5, h: 0.2,
    fontFace: 'Microsoft YaHei', fontSize: 9.4, color: C.muted, margin: 0
  });
  addFooter(slide, '07');
}

// Slide 8
{
  const slide = pptx.addSlide();
  addBg(slide);
  addHeader(slide, '研发组织与年度推进建议', '我的建议是：以现有产品线为牵引，从单场景智能助手逐步升级到多智能体协同平台，形成公司第二增长曲线。');
  addLogoTag(slide);

  slide.addImage({ path: IMG.fault, x: 8.95, y: 1.44, w: 3.1, h: 2.14 });
  slide.addShape(pptx.ShapeType.rect, { x: 8.95, y: 1.44, w: 3.1, h: 2.14, line: { color: C.navy, transparency: 100 }, fill: { color: C.navy, transparency: 78 } });
  slide.addText('2026 年建议目标', {
    x: 9.24, y: 1.78, w: 2.2, h: 0.22,
    fontFace: 'Microsoft YaHei', fontSize: 14, bold: true, color: C.white,
    margin: 0
  });
  addBulletList(slide, [
    '完成 AI 中台 1.0；',
    '落地 3 个标杆 Agent 项目；',
    '形成统一评测与安全机制；',
    '发布面向客户的 Agent 化产品版本。'
  ], { x: 9.16, y: 2.12, w: 2.48, h: 1.18, fontSize: 10.1, color: C.white, bulletIndent: 10, hanging: 2.4, spaceAfterPt: 4 });

  card(slide, { x: 0.82, y: 1.48, w: 2.86, h: 1.72, title: '1. 平台与大模型组', body: '负责知识库、RAG、权限、安全、日志、Agent编排与评测体系。', accent: C.blue });
  card(slide, { x: 3.92, y: 1.48, w: 2.86, h: 1.72, title: '2. 电力算法组', body: '负责预测、故障诊断、优化求解、仿真校核等专业模型持续演进。', accent: C.teal });
  card(slide, { x: 0.82, y: 3.52, w: 2.86, h: 1.72, title: '3. 产品与集成组', body: '负责把Agent嵌入现有产品与项目交付流程，形成客户可见价值。', accent: C.cyan });
  card(slide, { x: 3.92, y: 3.52, w: 2.86, h: 1.72, title: '4. 场景验证组', body: '对接标杆客户、项目现场和合作院校，形成数据回流与商业样板。', accent: C.accent });

  sectionBar(slide, 7.2, 4.08, 1.9, '结论');
  slide.addText('益帕瓦已经具备切入“电力AI智能体”的业务土壤。\n只要坚持“先场景、后平台；先闭环、后规模”的节奏，就有机会把现有咨询能力和产品能力升级为更强的行业竞争壁垒。', {
    x: 7.22, y: 4.52, w: 5.05, h: 1.26,
    fontFace: 'Microsoft YaHei', fontSize: 12.6, color: C.text,
    bold: true, margin: 0
  });
  slide.addText('建议下一步：优先确定 1 个故障诊断标杆项目 + 1 个功率预测项目 + 1 个规划项目，作为 Agent 研发首批样板。', {
    x: 7.22, y: 6.02, w: 5.1, h: 0.36,
    fontFace: 'Microsoft YaHei', fontSize: 10.4, color: C.muted, margin: 0
  });
  addFooter(slide, '08');
}

(async () => {
  const out = '益帕瓦智慧能源业务AI智能体研发规划.pptx';
  await pptx.writeFile({ fileName: out });
  console.log(`Generated ${out}`);
})();
