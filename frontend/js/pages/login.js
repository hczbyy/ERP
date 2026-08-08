/* ============================================================
 * 登录页
 * ============================================================ */
(function () {
  window.Pages = window.Pages || {};

  Pages.login = {
    init() {
      const form = document.getElementById("login-form");
      const uInput = document.getElementById("login-username");
      const pInput = document.getElementById("login-password");
      const btn = document.getElementById("login-btn");

      // 点击演示账号自动填充
      document.querySelectorAll(".tip-chips .chip").forEach((chip) => {
        chip.addEventListener("click", () => {
          uInput.value = chip.dataset.u;
          pInput.value = chip.dataset.p;
          uInput.focus();
        });
      });

      form.addEventListener("submit", async (e) => {
        e.preventDefault();
        btn.disabled = true;
        btn.textContent = "登录中...";
        try {
          const data = await API.post("/api/auth/login", {
            username: uInput.value.trim(),
            password: pInput.value,
          });
          API.saveToken(data.token);
          UI.toast("登录成功");
          await ERP.bootstrap();
        } catch (err) {
          UI.err(err);
        } finally {
          btn.disabled = false;
          btn.textContent = "登 录";
        }
      });
    },
  };
})();