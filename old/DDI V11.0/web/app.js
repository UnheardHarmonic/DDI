const form = document.querySelector("#task-form");
const companyList = document.querySelector("#company-list");
const dataType = document.querySelector("#data-type");
const submitButton = document.querySelector("#submit-button");
const statusTitle = document.querySelector("#status-title");
const statusMessage = document.querySelector("#status-message");
const statusResult = document.querySelector("#status-result");
const downloadList = document.querySelector("#download-list");

// 定义临时访问口令的会话存储键名。
const temporaryAccessKeyStorageName = "ddi-temporary-access-key";

// 定义临时访问者标识的会话存储键名。
const temporaryVisitorIdStorageName = "ddi-temporary-visitor-id";

// 保存所有接口请求需要附加的认证头。
let requestAuthenticationHeaders = {};

// 创建当前浏览器会话的随机访问者标识。
const createTemporaryVisitorId = () => crypto.randomUUID();

// 读取或创建当前浏览器会话的访问者标识。
const getTemporaryVisitorId = () => {
  // 读取现有的浏览器会话访问者标识。
  let visitorId = sessionStorage.getItem(temporaryVisitorIdStorageName);

  // 在访问者标识不存在时创建新的随机标识。
  if (!visitorId) {
    // 生成当前浏览器会话的随机访问者标识。
    visitorId = createTemporaryVisitorId();

    // 保存随机访问者标识到当前浏览器会话。
    sessionStorage.setItem(temporaryVisitorIdStorageName, visitorId);
  }

  // 返回当前浏览器会话的访问者标识。
  return visitorId;
};

// 加载服务认证模式并准备接口认证头。
const configureAuthentication = async () => {
  // 获取服务当前公开的认证模式。
  const response = await fetch("/api/authentication-mode");

  // 读取认证模式响应内容。
  const authentication = await response.json();

  // 在认证模式接口异常时终止初始化。
  if (!response.ok) throw new Error(authentication.detail || "无法读取访问认证配置");

  // 在 Cloudflare Access 模式下不额外添加浏览器认证头。
  if (authentication.mode === "cloudflare_access") return;

  // 读取当前浏览器会话已保存的临时访问口令。
  let accessKey = sessionStorage.getItem(temporaryAccessKeyStorageName);

  // 在临时访问口令不存在时向访问者请求输入。
  if (!accessKey) {
    // 读取访问者输入的临时访问口令。
    accessKey = window.prompt("请输入管理员提供的临时访问口令：", "");
  }

  // 拒绝未输入临时访问口令的浏览器会话。
  if (!accessKey) throw new Error("需要临时访问口令才能使用网页任务台");

  // 保存临时访问口令到当前浏览器会话。
  sessionStorage.setItem(temporaryAccessKeyStorageName, accessKey);

  // 保存临时模式下所有接口请求所需的认证头。
  requestAuthenticationHeaders = {
    "X-DDI-Access-Key": accessKey,
    "X-DDI-Visitor-Id": getTemporaryVisitorId(),
  };
};

// 下载已归属当前浏览器会话的任务文件。
const downloadArtifact = async (taskId, artifact) => {
  // 请求当前访问者有权限读取的任务归档文件。
  const response = await fetch(`/api/tasks/${taskId}/downloads/${encodeURIComponent(artifact)}`, { headers: requestAuthenticationHeaders });

  // 在文件下载请求失败时读取接口错误内容。
  if (!response.ok) {
    // 读取服务端返回的错误信息。
    const error = await response.json();

    // 抛出浏览器可显示的下载失败异常。
    throw new Error(error.detail || "无法下载任务文件");
  }

  // 将任务文件响应转换为浏览器 Blob 对象。
  const fileBlob = await response.blob();

  // 创建当前 Blob 对应的临时下载地址。
  const downloadUrl = URL.createObjectURL(fileBlob);

  // 创建浏览器原生下载链接元素。
  const downloadAnchor = document.createElement("a");

  // 设置临时下载地址。
  downloadAnchor.href = downloadUrl;

  // 设置浏览器保存的任务文件名称。
  downloadAnchor.download = artifact;

  // 触发浏览器下载任务文件。
  downloadAnchor.click();

  // 释放不再使用的 Blob 下载地址。
  URL.revokeObjectURL(downloadUrl);
};

let activeTaskId = "";

const setStatus = (title, message, result) => {
  statusTitle.textContent = title;
  statusMessage.textContent = message;
  statusResult.hidden = !result;
  statusResult.textContent = result ? JSON.stringify(result, null, 2) : "";
};

const setDownloads = (taskId, artifacts) => {
  downloadList.replaceChildren(...artifacts.map((artifact) => {
    const link = document.createElement("a");
    link.className = "download-link";
    link.href = "#";
    link.textContent = `下载 ${artifact}`;
    link.addEventListener("click", async (event) => {
      event.preventDefault();
      try {
        await downloadArtifact(taskId, artifact);
      } catch (error) {
        setStatus("下载失败", error.message, null);
      }
    });
    return link;
  }));
  downloadList.hidden = !artifacts.length;
};

const loadOptions = async () => {
  const response = await fetch("/api/options", { headers: requestAuthenticationHeaders });
  const options = await response.json();
  if (!response.ok) throw new Error(options.detail || "无法读取网页配置");
  companyList.replaceChildren(...options.companies.map((company) => {
    const label = document.createElement("label");
    const checkbox = document.createElement("input");
    const text = document.createElement("span");
    const platform = document.createElement("small");
    label.className = "company-choice";
    checkbox.type = "checkbox";
    checkbox.name = "company";
    checkbox.value = company.name;
    text.textContent = company.name;
    platform.textContent = company.platform;
    label.append(checkbox, text, platform);
    return label;
  }));
  dataType.replaceChildren(...options.data_types.map((value) => new Option(value, value)));
};

const pollTask = async () => {
  const response = await fetch(`/api/tasks/${activeTaskId}`, { headers: requestAuthenticationHeaders });
  const task = await response.json();
  if (!response.ok) throw new Error(task.detail || "无法读取任务状态");
  setStatus(task.status, task.message, task.result);
  setDownloads(task.task_id, task.artifacts || []);
  if (["已完成", "失败"].includes(task.status)) {
    submitButton.disabled = false;
    submitButton.textContent = "提交任务";
    return;
  }
  window.setTimeout(pollTask, 2000);
};

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const companies = [...document.querySelectorAll("input[name=company]:checked")].map((element) => element.value);
  if (!companies.length) return setStatus("需要选择商业", "请至少选择一家商业后再提交。", null);
  submitButton.disabled = true;
  submitButton.textContent = "正在提交…";
  try {
    const response = await fetch("/api/tasks", { method: "POST", headers: { "Content-Type": "application/json", ...requestAuthenticationHeaders }, body: JSON.stringify({ companies, data_type: dataType.value, start_date: document.querySelector("#start-date").value, end_date: document.querySelector("#end-date").value, max_workers: Number(document.querySelector("#max-workers").value), copy_excel: document.querySelector("#copy-excel").checked }) });
    const task = await response.json();
    if (!response.ok) throw new Error(task.detail || "无法创建任务");
    activeTaskId = task.task_id;
    setStatus(task.status, task.message, null);
    setDownloads("", []);
    submitButton.textContent = "任务执行中…";
    window.setTimeout(pollTask, 1000);
  } catch (error) {
    setStatus("提交失败", error.message, null);
    submitButton.disabled = false;
    submitButton.textContent = "提交任务";
  }
});

configureAuthentication().then(loadOptions).catch((error) => setStatus("无法加载", error.message, null));
