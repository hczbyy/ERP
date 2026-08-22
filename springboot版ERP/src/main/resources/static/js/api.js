/* ============================================================
 * API 封装：token 管理 + 统一响应处理
 * ============================================================ */
(function () {
  const TOKEN_KEY = "erp_token";

  async function request(path, method = "GET", body = null) {
    const headers = { "Content-Type": "application/json" };
    const token = localStorage.getItem(TOKEN_KEY);
    if (token) headers.Authorization = "Bearer " + token;

    let resp;
    try {
      resp = await fetch(path, {
        method,
        headers,
        body: body === null ? undefined : JSON.stringify(body),
      });
    } catch (e) {
      throw new Error("网络异常，请确认后端服务已启动");
    }

    // 401：未登录或过期，跳回登录页
    if (resp.status === 401) {
      localStorage.removeItem(TOKEN_KEY);
      location.hash = "#/login";
      throw new Error("登录已过期，请重新登录");
    }

    const data = await resp.json().catch(() => ({}));
    if (data.code !== 0) {
      throw new Error(data.message || `请求失败(${resp.status})`);
    }
    return data.data;
  }

  window.API = {
    get: (p) => request(p),
    post: (p, b) => request(p, "POST", b),
    put: (p, b) => request(p, "PUT", b),
    del: (p) => request(p, "DELETE"),
    saveToken: (t) => localStorage.setItem(TOKEN_KEY, t),
    clearToken: () => localStorage.removeItem(TOKEN_KEY),
    hasToken: () => !!localStorage.getItem(TOKEN_KEY),
  };
})();