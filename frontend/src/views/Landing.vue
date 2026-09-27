<template>
  <div class="landing-root" :style="bgStyle" @mousemove="onMouseMove" @mouseleave="onMouseLeave">
    <header class="top-nav">
      <div class="top-nav-inner">
        <div class="brand" @click="scrollTo('hero')">
          <span class="brand-glyph">知</span>
          <span class="brand-name">AI 知识库</span>
        </div>
        <nav class="top-menu">
          <button v-for="item in navItems" :key="item.key" class="menu-btn" @click="scrollTo(item.key)">{{ item.label }}</button>
        </nav>
        <div class="top-actions">
          <button class="btn btn-secondary" @click="goToLogin">登录</button>
          <button class="btn btn-primary" @click="goToChat">立即体验</button>
        </div>
      </div>
    </header>

    <section id="hero" class="hero section-offset">
      <div class="hero-grid"></div>
      <div class="hero-glow hero-glow--one"></div>
      <div class="hero-glow hero-glow--two"></div>

      <div class="hero-content">
        <div class="hero-badge">
          <span class="hero-badge-dot"></span>
          RAG Knowledge Assistant
        </div>
        <h1 class="hero-title">让文档知识真正可对话</h1>
        <p class="hero-subtitle">
          你的项目支持文档上传、语义检索、多轮对话与来源追溯，
          将团队沉淀内容快速转化为可落地答案。
        </p>
        <div class="hero-actions">
          <button class="btn btn-primary" @click="goToChat">体验对话</button>
          <button class="btn btn-secondary" @click="scrollTo('technology')">查看技术架构</button>
        </div>

        <div class="stats-grid">
          <article class="stat-card" v-for="s in stats" :key="s.label">
            <div class="stat-value">{{ s.value }}</div>
            <div class="stat-label">{{ s.label }}</div>
          </article>
        </div>
      </div>
    </section>

    <section id="value" class="section section-offset">
      <div class="section-inner">
        <div class="section-head">
          <h2>核心价值</h2>
          <p>围绕“提效、准确、可追溯”构建企业级知识问答体验。</p>
        </div>
        <div class="feature-grid">
          <article class="feature-card" v-for="item in features" :key="item.title">
            <div class="feature-icon">{{ item.icon }}</div>
            <h3>{{ item.title }}</h3>
            <p>{{ item.desc }}</p>
          </article>
        </div>
      </div>
    </section>

    <section id="technology" class="section section-offset section-tech">
      <div class="section-inner">
        <div class="section-head">
          <h2>技术架构</h2>
          <p>从文档解析、向量化检索到大模型流式回答，完整覆盖 RAG 应用核心链路。</p>
        </div>

        <div class="architecture-card">
          <div class="architecture-flow">
            <div class="flow-node" v-for="node in architectureFlow" :key="node.title">
              <span class="flow-index">{{ node.index }}</span>
              <h3>{{ node.title }}</h3>
              <p>{{ node.desc }}</p>
            </div>
          </div>
        </div>

        <div class="tech-grid">
          <article class="tech-card" v-for="group in techStack" :key="group.title">
            <div class="tech-card-head">
              <span class="tech-icon">{{ group.icon }}</span>
              <div>
                <h3>{{ group.title }}</h3>
                <p>{{ group.desc }}</p>
              </div>
            </div>
            <div class="tech-tags">
              <span v-for="item in group.items" :key="item" class="tech-tag">{{ item }}</span>
            </div>
          </article>
        </div>

        <div class="pipeline-wrap">
          <div class="pipeline-head">
            <h3>RAG 处理流程</h3>
            <p>上传后的每份资料都会进入标准化处理链路，确保可检索、可引用、可追溯。</p>
          </div>
          <div class="pipeline-list">
            <article class="pipeline-item" v-for="step in pipelineSteps" :key="step.title">
              <div class="pipeline-num">{{ step.num }}</div>
              <div>
                <h4>{{ step.title }}</h4>
                <p>{{ step.desc }}</p>
              </div>
            </article>
          </div>
        </div>
      </div>
    </section>

    <section id="scenarios" class="section section-offset section-alt">
      <div class="section-inner">
        <div class="section-head">
          <h2>适用场景</h2>
          <p>覆盖常见知识型工作流，降低信息检索与沟通成本。</p>
        </div>
        <div class="scenario-grid">
          <article class="scenario-card" v-for="item in scenarios" :key="item.title">
            <h3>{{ item.title }}</h3>
            <p>{{ item.desc }}</p>
            <ul>
              <li v-for="point in item.points" :key="point">{{ point }}</li>
            </ul>
          </article>
        </div>
      </div>
    </section>

    <section id="trust" class="section section-offset">
      <div class="section-inner">
        <div class="section-head">
          <h2>信任背书</h2>
          <p>通过真实指标与反馈，降低用户决策顾虑。</p>
        </div>
        <div class="trust-grid">
          <article class="quote-card" v-for="q in quotes" :key="q.name">
            <p class="quote-text">“{{ q.text }}”</p>
            <div class="quote-meta">{{ q.name }} · {{ q.role }}</div>
          </article>
          <article class="badge-card">
            <h3>合作与兼容</h3>
            <div class="badge-row">
              <span class="badge-item" v-for="b in badges" :key="b">{{ b }}</span>
            </div>
          </article>
        </div>
      </div>
    </section>

    <section id="faq" class="section section-offset section-alt">
      <div class="section-inner faq-wrap">
        <div class="section-head">
          <h2>常见问题</h2>
          <p>上线前用户最常问的关键问题。</p>
        </div>
        <div class="faq-list">
          <details class="faq-item" v-for="f in faqs" :key="f.q">
            <summary>{{ f.q }}</summary>
            <p>{{ f.a }}</p>
          </details>
        </div>
      </div>
    </section>

    <section id="contact" class="section section-offset">
      <div class="section-inner contact-wrap">
        <div class="contact-card">
          <h2>联系与试用支持</h2>
          <p>
            若你希望接入企业知识、定制行业场景或配置私有化部署，
            可通过以下方式联系（你给我联系方式后我可替换为真实信息）。
          </p>
          <div class="contact-meta">
            <div><span>邮箱：</span>1432158894@qq.com</div>
            <div><span>电话：</span>13373968448</div>
            <div><span>地址：</span>河南省驻马店市黄淮学院</div>
          </div>
        </div>
      </div>
    </section>

    <footer class="footer">
      <div>© 2026 AI 知识库系统 · 备案号：110120119</div>
      <button class="to-top" v-show="showTop" @click="scrollTo('hero')">返回顶部</button>
    </footer>

    <button class="floating-cta" @click="goToChat">体验对话</button>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '../store'

const router = useRouter()
const store = useUserStore()
const showTop = ref(false)

const pointerX = ref(50)
const pointerY = ref(18)
const targetX = ref(50)
const targetY = ref(18)
let rafId = 0

const navItems = [
  { key: 'value', label: '核心价值' },
  { key: 'technology', label: '技术架构' },
  { key: 'scenarios', label: '适用场景' },
  { key: 'trust', label: '信任背书' },
  { key: 'faq', label: '常见问题' },
  { key: 'contact', label: '联系咨询' }
]

const stats = [
  { value: '10x', label: '检索效率提升' },
  { value: '95%', label: '答案相关性' },
  { value: '24/7', label: '智能问答可用' },
  { value: '100%', label: '来源可追溯' }
]

const features = [
  { icon: '文', title: '多格式文档处理', desc: '支持文档上传与内容解析，自动构建可检索知识库。' },
  { icon: '检', title: '语义检索增强', desc: '向量检索召回相关片段，回答更贴近你的业务语境。' },
  { icon: '答', title: '多轮对话连续性', desc: '按会话管理上下文，支持持续追问和历史沉淀。' },
  { icon: '源', title: '来源透明可追溯', desc: '回答附带参考来源，便于校验、复盘与交付。' },
  { icon: '管', title: '会话管理清晰', desc: '按首问聚合历史记录，快速定位每轮问题。' },
  { icon: '拓', title: '易扩展架构', desc: '可继续接入权限、知识标签、行业模板与自动化流程。' }
]

const architectureFlow = [
  { index: '01', title: '前端交互层', desc: 'Vue 3 + Element Plus 构建上传、检索、问答、管理后台与个人设置体验。' },
  { index: '02', title: '业务接口层', desc: 'FastAPI 提供用户认证、文档管理、会话管理、管理员管理和流式问答接口。' },
  { index: '03', title: '知识处理层', desc: '对 PDF、Word、文本、图片等资料进行解析、分块、清洗与元数据记录。' },
  { index: '04', title: '检索增强层', desc: '基于向量库召回相关片段，将命中文档作为上下文注入大模型。' },
  { index: '05', title: '大模型生成层', desc: '通过 OpenAI 兼容接口调用模型，使用 SSE 将回答 token 实时推送到页面。' }
]

const techStack = [
  {
    icon: '前',
    title: '前端技术',
    desc: '负责交互、状态、路由、Markdown 渲染和流式展示。',
    items: ['Vue 3', 'Vite', 'Pinia', 'Vue Router', 'Element Plus', 'Marked', 'DOMPurify', 'Fetch SSE']
  },
  {
    icon: '后',
    title: '后端技术',
    desc: '负责 API、权限、数据库、文件处理与流式响应。',
    items: ['FastAPI', 'Uvicorn', 'SQLAlchemy', 'Pydantic', 'JWT', 'Passlib bcrypt', 'StreamingResponse']
  },
  {
    icon: '知',
    title: '知识库能力',
    desc: '把非结构化资料转成可检索知识片段。',
    items: ['文档解析', '文本分块', '向量检索', '语义召回', '来源追溯', '分类检索', '指定文档问答']
  },
  {
    icon: '模',
    title: '模型接入',
    desc: '兼容可配置的大模型服务，支持用户自定义模型参数。',
    items: ['OpenAI Compatible API', '阿里云百炼', '自定义 Base URL', '自定义 Model', '用户级 API Key']
  },
  {
    icon: '安',
    title: '权限与安全',
    desc: '区分游客、普通用户和管理员，敏感信息不在前端明文暴露。',
    items: ['角色权限', '管理员后台', '密码哈希', 'Token 刷新', '用户级数据隔离', 'API Key 服务端保存']
  },
  {
    icon: '管',
    title: '运营管理',
    desc: '面向管理员提供系统可视化、用户和内容明细管理。',
    items: ['用户列表', '文档列表', '对话列表', '统计概览', '账号启停', '权限提权/撤权']
  }
]

const pipelineSteps = [
  { num: '1', title: '上传与分类', desc: '用户上传资料，可按分类管理文档，为后续按范围检索做准备。' },
  { num: '2', title: '解析与清洗', desc: '提取文档正文、表格和图片 OCR/识别结果，转换为统一文本内容。' },
  { num: '3', title: '切分与入库', desc: '按语义长度切分知识片段，记录文件名、用户、分类、字数和分块数量。' },
  { num: '4', title: '向量召回', desc: '提问时按分类或指定文档检索最相关片段，减少模型胡编风险。' },
  { num: '5', title: '流式生成', desc: '模型边生成边返回，前端实时渲染 Markdown，提高等待体验。' },
  { num: '6', title: '保存与追溯', desc: '保存用户问题、AI 回答、会话记录和参考来源，便于复盘与管理。' }
]

const scenarios = [
  {
    title: '企业知识库问答',
    desc: '面对制度、流程、产品资料时，快速提取关键结论。',
    points: ['新人培训与上手', '跨部门信息同步', '制度条款快速查询']
  },
  {
    title: '项目文档协同',
    desc: '围绕需求、设计、测试文档进行统一对话检索。',
    points: ['需求理解与澄清', '接口与逻辑复核', '交付前知识回顾']
  },
  {
    title: '客服与运营支持',
    desc: '沉淀常见问题与标准答案，降低重复沟通成本。',
    points: ['FAQ 自动回复', '运营活动问答', '标准话术一致性']
  }
]

const quotes = [
  { name: '产品负责人 A', role: 'SaaS 团队', text: '以前找文档要翻很多页，现在一句话直接定位到关键段落。' },
  { name: '运营经理 B', role: '内容团队', text: '把运营手册接入后，新人上手明显更快，问答质量也更稳定。' }
]

const badges = ['RAG', '向量检索', '会话历史', '来源追溯', '图片文档支持', '可扩展 API']

const faqs = [
  { q: '需要先登录才能体验吗？', a: '不需要。点击“体验对话”会自动进入游客模式，直接开始对话。' },
  { q: '支持哪些文档类型？', a: '当前支持文本与图片文档场景，后续可继续扩展更多格式。' },
  { q: '回答可以查看依据吗？', a: '可以。系统会返回参考来源，方便核验与追溯。' },
  { q: '是否可以接入公司内部系统？', a: '可以。后端提供可扩展接口，可按你的业务流程接入。' }
]

const goToLogin = () => {
  router.push('/login')
}

const goToChat = () => {
  if (!store.isAuthenticated) {
    store.setGuestMode()
  }
  router.push('/chat')
}

const scrollTo = (id) => {
  const target = document.getElementById(id)
  if (!target) return
  target.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

const animateGlow = () => {
  pointerX.value += (targetX.value - pointerX.value) * 0.08
  pointerY.value += (targetY.value - pointerY.value) * 0.08
  rafId = window.requestAnimationFrame(animateGlow)
}

const onMouseMove = (event) => {
  const width = window.innerWidth || 1
  const height = window.innerHeight || 1
  targetX.value = (event.clientX / width) * 100
  targetY.value = (event.clientY / height) * 100
}

const onMouseLeave = () => {
  targetX.value = 50
  targetY.value = 18
}

const bgStyle = computed(() => ({
  '--mx': `${pointerX.value}%`,
  '--my': `${pointerY.value}%`
}))

const onScroll = () => {
  showTop.value = window.scrollY > 480
}

onMounted(() => {
  window.addEventListener('scroll', onScroll)
  animateGlow()
})

onBeforeUnmount(() => {
  window.removeEventListener('scroll', onScroll)
  if (rafId) window.cancelAnimationFrame(rafId)
})
</script>

<style scoped>
.landing-root {
  min-height: 100vh;
  background:
    radial-gradient(
      circle 500px at var(--mx, 50%) var(--my, 18%),
      rgba(79, 111, 220, .10),
      rgba(79, 111, 220, 0) 72%
    ),
    radial-gradient(
      circle 360px at calc(var(--mx, 50%) + 14%) calc(var(--my, 18%) + 10%),
      rgba(205, 220, 252, .24),
      rgba(205, 220, 252, 0) 74%
    ),
    radial-gradient(
      circle 320px at calc(var(--mx, 50%) - 18%) calc(var(--my, 18%) + 18%),
      rgba(79, 111, 220, .06),
      rgba(79, 111, 220, 0) 78%
    ),
    var(--c-bg);
  color: var(--c-text);
  transition: background .16s linear;
}

.top-nav {
  position: sticky;
  top: 0;
  z-index: 30;
  backdrop-filter: blur(10px);
  background: rgba(255, 255, 255, .86);
  border-bottom: 1px solid rgba(179, 229, 252, .8);
}
.top-nav-inner {
  max-width: 1160px;
  margin: 0 auto;
  padding: 10px 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.brand {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}
.brand-glyph {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  background: linear-gradient(135deg, var(--c-accent), #0288d1);
  font-family: var(--font-serif);
  font-weight: 700;
}
.brand-name {
  font-weight: 700;
  letter-spacing: .02em;
}
.top-menu {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}
.menu-btn {
  border: none;
  background: transparent;
  color: var(--c-text-2);
  padding: 6px 10px;
  border-radius: var(--r-sm);
  cursor: pointer;
  font-size: 13px;
}
.menu-btn:hover {
  background: var(--c-elevated);
  color: var(--c-text);
}
.top-actions {
  display: flex;
  gap: 8px;
}

.section-offset {
  scroll-margin-top: 74px;
}

.hero {
  position: relative;
  overflow: hidden;
  padding: 84px 24px 56px;
  border-bottom: 1px solid var(--c-border);
  background: linear-gradient(180deg, rgba(250, 252, 255, .92) 0%, rgba(255, 255, 255, .96) 100%);
}
.hero-grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(79,111,220,.04) 1px, transparent 1px),
    linear-gradient(90deg, rgba(79,111,220,.04) 1px, transparent 1px);
  background-size: 28px 28px;
  pointer-events: none;
}
.hero-glow {
  position: absolute;
  border-radius: 50%;
  filter: blur(42px);
  pointer-events: none;
}
.hero-glow--one {
  width: 320px;
  height: 320px;
  right: -80px;
  top: -70px;
  background: rgba(79,111,220,.11);
}
.hero-glow--two {
  width: 260px;
  height: 260px;
  left: -80px;
  bottom: -90px;
  background: rgba(205,220,252,.22);
}
.hero-content {
  position: relative;
  z-index: 1;
  max-width: 1080px;
  margin: 0 auto;
  text-align: center;
}
.hero-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  border: 1px solid rgba(2,119,189,.22);
  background: var(--c-accent-dim);
  border-radius: 999px;
  color: var(--c-accent);
  font-size: 12px;
  font-weight: 600;
  letter-spacing: .04em;
}
.hero-badge-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--c-ok);
  box-shadow: 0 0 6px rgba(46,125,50,.4);
}
.hero-title {
  margin: 18px 0 12px;
  font-family: var(--font-serif);
  font-size: 44px;
  line-height: 1.2;
}
.hero-subtitle {
  margin: 0 auto;
  max-width: 760px;
  font-size: 16px;
  line-height: 1.8;
  color: var(--c-text-2);
}
.hero-actions {
  margin-top: 28px;
  display: flex;
  justify-content: center;
  gap: 12px;
  flex-wrap: wrap;
}
.stats-grid {
  margin-top: 30px;
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}
.stat-card {
  background: var(--c-elevated);
  border: 1px solid #e9eef6;
  border-radius: var(--r-md);
  box-shadow: var(--shadow-sm);
  padding: 14px;
}
.stat-value {
  color: var(--c-accent);
  font-size: 24px;
  font-weight: 700;
}
.stat-label {
  margin-top: 4px;
  color: var(--c-text-2);
  font-size: 12px;
}

.section {
  padding: 56px 24px;
}
.section-alt {
  background: linear-gradient(180deg, rgba(252, 254, 255, .78) 0%, rgba(246, 251, 255, .78) 100%);
  border-top: 1px solid var(--c-border);
  border-bottom: 1px solid var(--c-border);
}
.section-inner {
  max-width: 1120px;
  margin: 0 auto;
}
.section-head {
  text-align: center;
  margin-bottom: 24px;
}
.section-head h2 {
  margin: 0;
  font-size: 32px;
  font-family: var(--font-serif);
}
.section-head p {
  margin-top: 10px;
  color: var(--c-text-2);
}

.feature-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}
.feature-card {
  background: var(--c-surface);
  border: 1px solid var(--c-border);
  border-radius: var(--r-lg);
  padding: 18px;
  box-shadow: var(--shadow-sm);
}
.feature-icon {
  width: 34px;
  height: 34px;
  border-radius: var(--r-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--c-accent-dim);
  color: var(--c-accent);
  font-weight: 700;
  margin-bottom: 10px;
}
.feature-card h3 {
  margin: 0;
  font-size: 16px;
}
.feature-card p {
  margin: 8px 0 0;
  color: var(--c-text-2);
  font-size: 13px;
  line-height: 1.7;
}

.section-tech {
  background:
    radial-gradient(circle at 18% 12%, rgba(79,111,220,.08), transparent 28%),
    radial-gradient(circle at 82% 18%, rgba(127,153,232,.10), transparent 30%),
    linear-gradient(180deg, #ffffff 0%, #f7faff 100%);
  border-top: 1px solid var(--c-border);
}
.architecture-card {
  position: relative;
  overflow: hidden;
  margin-bottom: 16px;
  border: 1px solid rgba(79,111,220,.16);
  border-radius: var(--r-xl);
  background: rgba(255,255,255,.76);
  box-shadow: var(--shadow-md);
  padding: 20px;
}
.architecture-card::before {
  content: '';
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(79,111,220,.05) 1px, transparent 1px),
    linear-gradient(90deg, rgba(79,111,220,.05) 1px, transparent 1px);
  background-size: 24px 24px;
  pointer-events: none;
}
.architecture-flow {
  position: relative;
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 12px;
  z-index: 1;
}
.flow-node {
  position: relative;
  min-height: 170px;
  border: 1px solid #e9eef6;
  border-radius: var(--r-lg);
  background: linear-gradient(180deg, #ffffff, #f7fbff);
  padding: 16px;
  box-shadow: var(--shadow-sm);
}
.flow-node:not(:last-child)::after {
  content: '→';
  position: absolute;
  top: 22px;
  right: -13px;
  z-index: 2;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--c-accent);
  background: #fff;
  border: 1px solid rgba(79,111,220,.18);
  box-shadow: var(--shadow-sm);
}
.flow-index {
  display: inline-flex;
  margin-bottom: 12px;
  padding: 3px 8px;
  border-radius: 999px;
  color: var(--c-accent);
  background: var(--c-accent-dim);
  font-size: 11px;
  font-weight: 800;
}
.flow-node h3 {
  margin: 0;
  font-size: 15px;
}
.flow-node p {
  margin: 8px 0 0;
  color: var(--c-text-2);
  font-size: 12px;
  line-height: 1.7;
}
.tech-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
  margin-top: 16px;
}
.tech-card {
  background: var(--c-elevated);
  border: 1px solid #e9eef6;
  border-radius: var(--r-lg);
  box-shadow: var(--shadow-sm);
  padding: 18px;
}
.tech-card-head {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 12px;
}
.tech-icon {
  width: 36px;
  height: 36px;
  border-radius: 12px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  background: linear-gradient(135deg, var(--c-accent), #7f99e8);
  font-weight: 800;
  box-shadow: var(--glow-accent-soft);
}
.tech-card h3 {
  margin: 0;
  font-size: 16px;
}
.tech-card p {
  margin: 5px 0 0;
  color: var(--c-text-2);
  font-size: 12px;
  line-height: 1.7;
}
.tech-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
}
.tech-tag {
  padding: 5px 9px;
  border-radius: 999px;
  background: #f6f9ff;
  border: 1px solid rgba(79,111,220,.14);
  color: var(--c-text-2);
  font-size: 11px;
  font-weight: 600;
}
.pipeline-wrap {
  margin-top: 16px;
  border: 1px solid var(--c-border);
  border-radius: var(--r-xl);
  background: linear-gradient(180deg, #ffffff, #f9fcff);
  box-shadow: var(--shadow-sm);
  padding: 20px;
}
.pipeline-head {
  display: flex;
  justify-content: space-between;
  gap: 24px;
  align-items: flex-end;
  margin-bottom: 14px;
}
.pipeline-head h3 {
  margin: 0;
  font-size: 20px;
  font-family: var(--font-serif);
}
.pipeline-head p {
  max-width: 560px;
  margin: 0;
  color: var(--c-text-2);
  font-size: 13px;
  line-height: 1.7;
}
.pipeline-list {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}
.pipeline-item {
  display: flex;
  gap: 12px;
  padding: 14px;
  border-radius: var(--r-lg);
  background: #fbfdff;
  border: 1px solid #e9eef6;
}
.pipeline-num {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--c-accent);
  background: var(--c-accent-dim);
  font-weight: 800;
}
.pipeline-item h4 {
  margin: 0;
  font-size: 14px;
}
.pipeline-item p {
  margin: 5px 0 0;
  color: var(--c-text-2);
  font-size: 12px;
  line-height: 1.7;
}

.scenario-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}
.scenario-card {
  background: var(--c-elevated);
  border: 1px solid #e9eef6;
  border-radius: var(--r-lg);
  box-shadow: var(--shadow-sm);
  padding: 18px;
}
.scenario-card h3 {
  margin: 0;
  font-size: 17px;
}
.scenario-card p {
  color: var(--c-text-2);
  margin: 8px 0 10px;
}
.scenario-card ul {
  margin: 0;
  padding-left: 18px;
  color: var(--c-text-2);
  line-height: 1.8;
  font-size: 13px;
}

.trust-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}
.quote-card,
.badge-card {
  background: var(--c-surface);
  border: 1px solid var(--c-border);
  border-radius: var(--r-lg);
  padding: 18px;
}
.quote-text {
  margin: 0;
  color: var(--c-text);
  line-height: 1.8;
}
.quote-meta {
  margin-top: 10px;
  font-size: 12px;
  color: var(--c-text-2);
}
.badge-card h3 {
  margin: 0 0 12px;
}
.badge-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.badge-item {
  padding: 5px 10px;
  border-radius: 999px;
  font-size: 12px;
  color: var(--c-accent);
  background: var(--c-accent-dim);
  border: 1px solid rgba(79,111,220,.2);
}

.faq-wrap {
  max-width: 900px;
}
.faq-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.faq-item {
  border: 1px solid var(--c-border);
  border-radius: var(--r-md);
  background: #fff;
  padding: 10px 14px;
}
.faq-item summary {
  cursor: pointer;
  font-weight: 600;
  color: var(--c-text);
}
.faq-item p {
  margin: 10px 0 0;
  color: var(--c-text-2);
  line-height: 1.8;
  font-size: 13px;
}

.contact-wrap {
  max-width: 900px;
}
.contact-card {
  border: 1px solid var(--c-border);
  border-radius: var(--r-lg);
  background: linear-gradient(180deg, #ffffff 0%, #f8fcff 100%);
  padding: 24px;
  box-shadow: var(--shadow-sm);
}
.contact-card h2 {
  margin: 0;
  font-family: var(--font-serif);
}
.contact-card p {
  color: var(--c-text-2);
  line-height: 1.8;
  margin: 10px 0 14px;
}
.contact-meta {
  display: grid;
  grid-template-columns: 1fr;
  gap: 6px;
  font-size: 14px;
  color: var(--c-text);
}
.contact-meta span {
  color: var(--c-text-2);
}
.contact-actions {
  margin-top: 16px;
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.footer {
  border-top: 1px solid var(--c-border);
  padding: 18px 24px 26px;
  max-width: 1120px;
  margin: 0 auto;
  display: flex;
  justify-content: space-between;
  align-items: center;
  color: var(--c-text-3);
  font-size: 12px;
}

.btn {
  border: 1px solid transparent;
  border-radius: var(--r-md);
  padding: 10px 16px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all .15s ease;
  position: relative;
  overflow: hidden;
}
.btn::before {
  content: '';
  position: absolute;
  inset: 1px 1px auto 1px;
  height: 42%;
  border-radius: inherit;
  background: linear-gradient(180deg, rgba(255,255,255,.42) 0%, rgba(255,255,255,0) 100%);
  pointer-events: none;
}
.btn-primary {
  color: #fff;
  background: linear-gradient(135deg, var(--c-accent), #7f99e8);
  box-shadow: var(--glow-accent-soft);
}
.btn-primary:hover {
  transform: translateY(-1px);
  opacity: .96;
  box-shadow: var(--glow-accent);
}
.btn-primary:active {
  transform: translateY(1px) scale(.987);
  box-shadow: var(--glow-press);
}
.btn-secondary {
  color: var(--c-text-2);
  background: var(--c-elevated);
  border-color: var(--c-border);
}
.btn-secondary:hover {
  background: #f4f8ff;
  color: var(--c-text);
}

.floating-cta {
  position: fixed;
  right: 18px;
  bottom: 18px;
  z-index: 40;
  border: none;
  border-radius: 999px;
  padding: 10px 14px;
  font-size: 13px;
  font-weight: 700;
  color: #fff;
  background: linear-gradient(135deg, var(--c-accent), #7f99e8);
  box-shadow: var(--glow-accent);
  cursor: pointer;
}
.to-top {
  border: 1px solid var(--c-border);
  background: var(--c-elevated);
  color: var(--c-text-2);
  border-radius: var(--r-sm);
  padding: 6px 10px;
  cursor: pointer;
}
.to-top:hover {
  background: var(--c-border);
}

@media (max-width: 980px) {
  .top-menu {
    display: none;
  }
  .hero-title {
    font-size: 34px;
  }
  .stats-grid,
  .feature-grid,
  .architecture-flow,
  .tech-grid,
  .pipeline-list,
  .scenario-grid,
  .trust-grid {
    grid-template-columns: 1fr;
  }
  .flow-node:not(:last-child)::after {
    content: '↓';
    top: auto;
    right: 50%;
    bottom: -13px;
    transform: translateX(50%);
  }
  .pipeline-head {
    align-items: flex-start;
    flex-direction: column;
    gap: 8px;
  }
}
</style>
