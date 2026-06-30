const state = {
  userId: "user_demo",
  portfolios: [],
  watch: [],
  journals: [],
  tasks: [],
  schedules: [],
  channels: [],
  notifications: [],
  evaluation: null,
  selectedTaskId: "",
};

const subtitles = {
  overview: "从持仓录入到报告、通知和轨迹审计的端到端演示。",
  portfolio: "创建或上传持仓组合，作为所有 Agent 任务的输入。",
  watchlist: "维护公告雷达和价格提醒关注池。",
  journal: "记录交易理由，用于 ReviewAgent 做后续复盘。",
  schedule: "手动或批量触发主动风险扫描。",
  notify: "配置飞书群机器人或 CLI 私聊通知。",
  tasks: "创建任务并触发金融、公告、复盘和报告 Agent。",
  report: "查看已归档的 Markdown 持仓体检报告。",
  trace: "审计 AgentRunRecord 和 ToolCallRecord。",
  evaluation: "运行最小评估集，展示工具调用、风险识别、安全审查和端到端完成率。",
};

function $(id) { return document.getElementById(id); }

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const payload = await response.json();
  if (!response.ok || !payload.success) {
    const message = payload?.error?.message || payload?.detail || response.statusText;
    throw new Error(message);
  }
  return payload.data;
}

function toast(message, error = false) {
  const node = $("toast");
  node.textContent = message;
  node.classList.toggle("error", error);
  node.hidden = false;
  setTimeout(() => { node.hidden = true; }, 3800);
}

function setLoading(button, loading) {
  if (!button) return;
  button.disabled = loading;
  if (loading) {
    button.dataset.label = button.textContent;
    button.textContent = "处理中...";
  } else if (button.dataset.label) {
    button.textContent = button.dataset.label;
  }
}

function currentUser() {
  state.userId = $("userId").value.trim() || "user_demo";
  return state.userId;
}

async function refreshAll() {
  const userId = currentUser();
  const [portfolios, watch, journals, tasks, schedules, channels, notifications] = await Promise.all([
    api(`/portfolios?user_id=${encodeURIComponent(userId)}`),
    api(`/watchlist?user_id=${encodeURIComponent(userId)}`),
    api(`/trade-journals?user_id=${encodeURIComponent(userId)}`),
    api(`/tasks?user_id=${encodeURIComponent(userId)}`),
    api(`/schedules?user_id=${encodeURIComponent(userId)}`),
    api(`/notification-channels?user_id=${encodeURIComponent(userId)}`),
    api(`/notification-channels/records?user_id=${encodeURIComponent(userId)}`),
  ]);
  Object.assign(state, { portfolios, watch, journals, tasks, schedules, channels, notifications });
  renderAll();
}

function renderAll() {
  $("metricPortfolios").textContent = state.portfolios.length;
  $("metricWatch").textContent = state.watch.length;
  $("metricTasks").textContent = state.tasks.length;
  $("metricNotifications").textContent = state.notifications.length;
  renderPortfolioList();
  renderWatchList();
  renderJournalList();
  renderScheduleList();
  renderChannels();
  renderNotifications();
  renderTaskList();
  renderEvaluation();
  fillSelects();
}

function table(headers, rows) {
  if (!rows.length) return `<p class="hint">暂无数据。</p>`;
  return `<table><thead><tr>${headers.map((h) => `<th>${h}</th>`).join("")}</tr></thead><tbody>${rows.join("")}</tbody></table>`;
}

function renderPortfolioList() {
  $("portfolioList").innerHTML = table(
    ["组合", "持仓", "创建时间", "操作"],
    state.portfolios.map((p) => {
      const holdings = (p.holdings || []).map((h) => `${h.symbol} ${h.name || ""} ${h.shares}股`).join("<br>");
      return `<tr><td>${p.name}<br><small>${p.portfolio_id}</small></td><td>${holdings}</td><td>${p.created_at}</td><td class="actions"><button class="btn small" data-create-task="${p.portfolio_id}">创建任务</button></td></tr>`;
    })
  );
}

function renderWatchList() {
  $("watchList").innerHTML = table(
    ["代码", "名称", "标签", "雷达", "操作"],
    state.watch.map((item) => `<tr><td>${item.symbol}</td><td>${item.name || "-"}</td><td>${(item.tags || []).map((t) => `<span class="tag">${t}</span>`).join("")}</td><td>公告 ${item.announcement_radar ? "开" : "关"} / 财务 ${item.financial_radar ? "开" : "关"}</td><td><button class="btn small" data-delete-watch="${item.watch_id}">删除</button></td></tr>`)
  );
}

function renderJournalList() {
  $("journalList").innerHTML = table(
    ["代码", "动作", "日期", "价格/数量", "理由"],
    state.journals.map((j) => `<tr><td>${j.symbol}</td><td>${j.action}</td><td>${j.trade_date}</td><td>${j.price || "-"} / ${j.shares || "-"}</td><td>${j.reason || "-"}</td></tr>`)
  );
}

function renderScheduleList() {
  $("scheduleList").innerHTML = table(
    ["类型", "目标", "状态", "跳过原因", "操作"],
    state.schedules.map((job) => `<tr><td>${job.job_type}</td><td>${job.target_id}</td><td>${job.status}</td><td>${job.last_skip_reason || "-"}</td><td class="actions"><button class="btn small" data-run-job="${job.job_id}">运行</button><button class="btn small" data-toggle-job="${job.job_id}" data-enabled="${!job.enabled}">${job.enabled ? "暂停" : "启用"}</button><button class="btn small" data-delete-job="${job.job_id}">删除</button></td></tr>`)
  );
}

function renderChannels() {
  $("channelList").innerHTML = table(
    ["类型", "名称", "目标", "事件", "操作"],
    state.channels.map((c) => `<tr><td>${c.channel_type}</td><td>${c.channel_name}</td><td>${c.webhook_url}</td><td>${(c.event_types || []).join(", ") || "全部"}</td><td><button class="btn small" data-test-channel="${c.channel_id}">测试</button></td></tr>`)
  );
}

function renderNotifications() {
  $("notificationList").innerHTML = table(
    ["事件", "标题", "状态", "重试", "错误"],
    state.notifications.map((n) => `<tr><td>${n.event_type}</td><td>${n.title}</td><td class="status-${n.status}">${n.status}</td><td>${n.retry_count}</td><td>${n.error_message || "-"}</td></tr>`)
  );
}

function renderTaskList() {
  $("taskList").innerHTML = table(
    ["任务", "状态", "Agent", "观察", "操作"],
    state.tasks.map((t) => `<tr><td>${t.task_id}<br><small>${t.created_at}</small></td><td class="status-${t.status}">${t.status}</td><td>${t.current_agent || "-"}</td><td>${t.latest_observation || t.error_message || "-"}</td><td class="actions"><button class="btn small" data-run-report="${t.task_id}">报告</button><button class="btn small" data-select-task="${t.task_id}">选中</button></td></tr>`)
  );
}

function pct(value) {
  return `${Math.round(Number(value || 0) * 1000) / 10}%`;
}

function renderEvaluation() {
  const metrics = $("evaluationMetrics");
  const suites = $("evaluationSuites");
  if (!metrics || !suites) return;
  if (!state.evaluation || !state.evaluation.summary) {
    metrics.innerHTML = `<p class="hint">尚未运行评估。</p>`;
    suites.innerHTML = "";
    return;
  }
  const summary = state.evaluation.summary;
  metrics.innerHTML = [
    ["工具调用准确率", pct(summary.tool_call_accuracy)],
    ["风险识别 F1", pct(summary.risk_identification_f1)],
    ["安全审查拦截率", pct(summary.guardrail_interception_rate)],
    ["端到端完成率", pct(summary.end_to_end_completion_rate)],
    ["稳定性通过率", pct(summary.stability_pass_rate)],
  ].map(([label, value]) => `<div class="metric"><span>${label}</span><strong>${value}</strong></div>`).join("");
  suites.innerHTML = Object.entries(state.evaluation.suites || {}).map(([name, suite]) => {
    const rows = (suite.details || []).map((item) => `<tr><td>${item.id}</td><td>${item.correct ?? item.passed}</td><td><pre>${JSON.stringify(item, null, 2)}</pre></td></tr>`);
    return `<div class="panel nested-panel"><div class="panel-head"><h3>${name}</h3><span class="hint">${suite.case_count} cases</span></div>${table(["用例", "通过", "详情"], rows)}</div>`;
  }).join("");
}

function fillSelects() {
  const portfolioOptions = state.portfolios.map((p) => `<option value="${p.portfolio_id}">${p.name} (${p.portfolio_id.slice(-6)})</option>`).join("");
  ["schedulePortfolio", "taskPortfolio"].forEach((id) => { $(id).innerHTML = portfolioOptions; });
  const taskOptions = state.tasks.map((t) => `<option value="${t.task_id}" ${t.task_id === state.selectedTaskId ? "selected" : ""}>${t.task_id} - ${t.status}</option>`).join("");
  ["reportTask", "traceTask"].forEach((id) => { $(id).innerHTML = taskOptions; });
}

function formData(form) {
  return Object.fromEntries(new FormData(form).entries());
}

function bindNavigation() {
  document.querySelectorAll(".nav-item").forEach((button) => {
    button.addEventListener("click", () => {
      const view = button.dataset.view;
      document.querySelectorAll(".nav-item").forEach((item) => item.classList.toggle("active", item === button));
      document.querySelectorAll(".view").forEach((item) => item.classList.toggle("active", item.id === `view-${view}`));
      $("viewTitle").textContent = button.textContent;
      $("viewSubtitle").textContent = subtitles[view] || "";
    });
  });
}

function bindForms() {
  $("refreshBtn").addEventListener("click", () => refreshAll().catch((e) => toast(e.message, true)));

  $("portfolioForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    const data = formData(event.currentTarget);
    await api("/portfolios", { method: "POST", body: JSON.stringify({ user_id: currentUser(), name: data.name, holdings: [{ symbol: data.symbol, name: data.stockName, shares: Number(data.shares), cost_price: Number(data.cost_price), buy_reason: data.buy_reason }] }) });
    toast("组合已创建。");
    await refreshAll();
  });

  $("csvForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    const file = $("csvFile").files[0];
    if (!file) return toast("请选择 CSV 文件。", true);
    const body = new FormData();
    body.append("file", file);
    const response = await fetch(`/portfolios/upload?user_id=${encodeURIComponent(currentUser())}`, { method: "POST", body });
    const payload = await response.json();
    if (!response.ok || !payload.success) throw new Error(payload.detail || payload.error?.message || "上传失败");
    toast(`上传完成，成功 ${payload.data.success_count} 条。`);
    await refreshAll();
  });

  $("watchForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    const data = formData(event.currentTarget);
    await api("/watchlist", { method: "POST", body: JSON.stringify({ user_id: currentUser(), symbol: data.symbol, name: data.name, tags: data.tags.split(",").map((x) => x.trim()).filter(Boolean) }) });
    toast("关注池已更新。");
    await refreshAll();
  });

  $("journalForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    const data = formData(event.currentTarget);
    data.user_id = currentUser();
    data.price = Number(data.price);
    data.shares = Number(data.shares);
    data.review_after_days = Number(data.review_after_days);
    await api("/trade-journals", { method: "POST", body: JSON.stringify(data) });
    toast("交易日志已保存。");
    await refreshAll();
  });

  $("scheduleForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    const data = formData(event.currentTarget);
    const enabled = event.currentTarget.querySelector("input[name='enabled']").checked;
    await api("/schedules", { method: "POST", body: JSON.stringify({ user_id: currentUser(), job_type: data.job_type, target_id: data.target_id, enabled }) });
    toast("定时任务已创建。");
    await refreshAll();
  });

  $("notifyForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    const data = formData(event.currentTarget);
    const endpoint = data.webhook_url;
    await api("/notification-channels", { method: "POST", body: JSON.stringify({ user_id: currentUser(), channel_type: data.channel_type, channel_name: data.channel_name, webhook_url: endpoint, user_open_id: endpoint, secret: data.secret, event_types: data.event_types.split(",").map((x) => x.trim()).filter(Boolean) }) });
    toast("飞书渠道已保存。");
    await refreshAll();
  });
}

function bindActions() {
  document.body.addEventListener("click", async (event) => {
    const target = event.target;
    if (!(target instanceof HTMLElement)) return;
    try {
      if (target.dataset.createTask) await createTask(target.dataset.createTask);
      if (target.dataset.deleteWatch) await api(`/watchlist/${target.dataset.deleteWatch}`, { method: "DELETE" });
      if (target.dataset.runJob) await api(`/schedules/${target.dataset.runJob}/run`, { method: "POST" });
      if (target.dataset.toggleJob) await api(`/schedules/${target.dataset.toggleJob}`, { method: "PATCH", body: JSON.stringify({ enabled: target.dataset.enabled === "true" }) });
      if (target.dataset.deleteJob) await api(`/schedules/${target.dataset.deleteJob}`, { method: "DELETE" });
      if (target.dataset.testChannel) await api(`/notification-channels/${target.dataset.testChannel}/test`, { method: "POST" });
      if (target.dataset.runReport) await runReport(target.dataset.runReport, target);
      if (target.dataset.selectTask) {
        state.selectedTaskId = target.dataset.selectTask;
        fillSelects();
        toast("任务已选中。");
        return;
      }
      if (target.dataset.createTask || target.dataset.deleteWatch || target.dataset.runJob || target.dataset.toggleJob || target.dataset.deleteJob || target.dataset.testChannel) {
        toast("操作完成。");
        await refreshAll();
      }
    } catch (error) {
      toast(error.message, true);
    }
  });

  $("createTaskBtn").addEventListener("click", () => createTask($("taskPortfolio").value).catch((e) => toast(e.message, true)));
  $("runReportBtn").addEventListener("click", () => runReport(state.selectedTaskId || state.tasks.at(-1)?.task_id || "", $("runReportBtn")).catch((e) => toast(e.message, true)));
  $("loadReportBtn").addEventListener("click", () => loadReport($("reportTask").value).catch((e) => toast(e.message, true)));
  $("loadTraceBtn").addEventListener("click", () => loadTrace($("traceTask").value).catch((e) => toast(e.message, true)));
  $("runEnabledBtn").addEventListener("click", async () => { await api("/schedules/run-enabled", { method: "POST", body: JSON.stringify({ user_id: currentUser() }) }); toast("已运行启用任务。"); await refreshAll(); });
  $("recoverBtn").addEventListener("click", async () => { const data = await api("/schedules/recover", { method: "POST", body: JSON.stringify({ user_id: currentUser() }) }); toast(`恢复 ${data.recovered_count} 个任务。`); await refreshAll(); });
  $("retryNotifyBtn").addEventListener("click", async () => { await api("/notification-channels/records/retry-failed", { method: "POST", body: JSON.stringify({ limit: 20 }) }); toast("已重试失败通知。"); await refreshAll(); });
  $("cliStatusBtn").addEventListener("click", async () => { const data = await api("/notification-channels/feishu-cli/status"); toast(`CLI installed=${data.installed}, authenticated=${data.authenticated}`); });
  $("runDemoBtn").addEventListener("click", runDemo);
  $("runEvalBtn").addEventListener("click", () => runEvaluation($("runEvalBtn")).catch((e) => toast(e.message, true)));
  $("loadEvalBtn").addEventListener("click", () => loadEvaluation().catch((e) => toast(e.message, true)));
}

async function createTask(portfolioId) {
  if (!portfolioId) throw new Error("请先选择或创建组合。");
  const task = await api("/tasks", { method: "POST", body: JSON.stringify({ user_id: currentUser(), portfolio_id: portfolioId }) });
  state.selectedTaskId = task.task_id;
  toast("任务已创建。");
  await refreshAll();
  return task;
}

async function runReport(taskId, button) {
  if (!taskId) throw new Error("请先创建或选择任务。");
  setLoading(button, true);
  try {
    const task = await api(`/tasks/${taskId}/run-report-check`, { method: "POST" });
    state.selectedTaskId = task.task_id;
    toast("报告任务完成。");
    await refreshAll();
    await loadReport(task.task_id);
    await loadTrace(task.task_id);
  } finally {
    setLoading(button, false);
  }
}

async function loadReport(taskId) {
  if (!taskId) throw new Error("请选择任务。");
  const report = await api(`/reports/tasks/${taskId}`);
  $("reportContent").textContent = report.markdown;
  state.selectedTaskId = taskId;
  fillSelects();
}

async function loadTrace(taskId) {
  if (!taskId) throw new Error("请选择任务。");
  const [runs, calls] = await Promise.all([api(`/tasks/${taskId}/agent-runs`), api(`/tasks/${taskId}/tool-calls`)]);
  $("agentRuns").innerHTML = runs.length ? runs.map((r) => `<div class="event"><strong>${r.agent_name} / ${r.action}</strong><p>${r.thought}</p><p>${r.observation}</p><small>${r.created_at}</small></div>`).join("") : `<p class="hint">暂无 Agent 轨迹。</p>`;
  $("toolCalls").innerHTML = calls.length ? calls.map((c) => `<div class="event"><strong>${c.tool_name} / ${c.success ? "success" : "failed"}</strong><p>${c.result_summary || c.error_message || "-"}</p><small>${c.created_at}</small></div>`).join("") : `<p class="hint">暂无工具调用。</p>`;
  state.selectedTaskId = taskId;
  fillSelects();
}

async function runDemo() {
  const button = $("runDemoBtn");
  const output = $("demoOutput");
  setLoading(button, true);
  try {
    const userId = currentUser();
    output.textContent = "创建演示组合...\n";
    const portfolio = await api("/portfolios", { method: "POST", body: JSON.stringify({ user_id: userId, name: "Day12 演示组合", holdings: [{ symbol: "300750", name: "宁德时代", shares: 100, cost_price: 235, buy_reason: "看好成长和业绩增长，长期持有。" }] }) });
    output.textContent += `组合: ${portfolio.portfolio_id}\n写入交易日志...\n`;
    await api("/trade-journals", { method: "POST", body: JSON.stringify({ user_id: userId, symbol: "300750", action: "buy", trade_date: new Date().toISOString().slice(0, 10), price: 235, shares: 100, reason: "看好成长和业绩增长，长期持有。" }) });
    output.textContent += "创建并运行报告任务...\n";
    const task = await api("/tasks", { method: "POST", body: JSON.stringify({ user_id: userId, portfolio_id: portfolio.portfolio_id }) });
    const completed = await api(`/tasks/${task.task_id}/run-report-check`, { method: "POST" });
    state.selectedTaskId = completed.task_id;
    output.textContent += `任务: ${completed.task_id} ${completed.status}\n读取报告和轨迹...\n`;
    await refreshAll();
    await loadReport(completed.task_id);
    await loadTrace(completed.task_id);
    output.textContent += "端到端体检完成。";
    toast("端到端演示完成。");
  } catch (error) {
    output.textContent += `失败: ${error.message}`;
    toast(error.message, true);
  } finally {
    setLoading(button, false);
  }
}

async function runEvaluation(button) {
  setLoading(button, true);
  try {
    state.evaluation = await api("/evaluations/run", { method: "POST" });
    renderEvaluation();
    toast("评估完成。");
  } finally {
    setLoading(button, false);
  }
}

async function loadEvaluation() {
  state.evaluation = await api("/evaluations/latest");
  renderEvaluation();
  toast(state.evaluation?.summary ? "已读取最近评估。" : "暂无最近评估。");
}

function initializeDefaults() {
  const dateInput = document.querySelector("input[name='trade_date']");
  if (dateInput) dateInput.value = new Date().toISOString().slice(0, 10);
}

bindNavigation();
bindForms();
bindActions();
initializeDefaults();
refreshAll().catch((error) => toast(error.message, true));
