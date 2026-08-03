// 后台发布函数：校验密码 → 把文章写入 GitHub 仓库 writing/ 文件夹 → Netlify 自动构建更新网站
exports.handler = async (event) => {
  const respond = (status, obj) => ({
    statusCode: status,
    headers: { 'Content-Type': 'application/json; charset=utf-8' },
    body: JSON.stringify(obj)
  });
  try {
    const body = JSON.parse(event.body || '{}');
    const { password, title, slug, date, excerpt, content } = body;

    // 1. 密码校验（密码存在 Netlify 环境变量里，不会出现在网页代码中）
    if (!process.env.ADMIN_PASSWORD || password !== process.env.ADMIN_PASSWORD) {
      return respond(401, { ok: false, error: '后台密码不对，请重试。' });
    }
    const t = (title || '').trim();
    const s = (slug || '').trim();
    const c = (content || '').trim();
    if (!t || !s || !c) return respond(400, { ok: false, error: '标题、文件名、正文都不能为空。' });
    if (!/^[A-Za-z0-9\-_]+$/.test(s)) {
      return respond(400, { ok: false, error: '文件名只能用英文字母、数字和连字符（-）。' });
    }
    if (!process.env.GITHUB_TOKEN) {
      return respond(500, { ok: false, error: '服务器缺少 GitHub 令牌配置，请先按说明在 Netlify 里设置环境变量。' });
    }

    // 2. 生成 Markdown 文章文件（frontmatter 供构建脚本读取）
    const esc = (v) => String(v || '').replace(/\\/g, '\\\\').replace(/"/g, '\\"');
    const md = `---\ntitle: "${esc(t)}"\nslug: ${s}\ndate: ${date || ''}\nexcerpt: "${esc(excerpt)}"\n---\n\n${c}\n`;

    // 3. 提交到 GitHub（同名文件 = 覆盖更新，先取原文件 sha）
    const api = 'https://api.github.com/repos/Aslindal/liqinglin-site/contents/writing/' + encodeURIComponent(s) + '.md';
    const headers = {
      Authorization: 'Bearer ' + process.env.GITHUB_TOKEN,
      Accept: 'application/vnd.github+json',
      'Content-Type': 'application/json'
    };
    let sha = null;
    const existing = await fetch(api, { headers });
    if (existing.ok) {
      const j = await existing.json();
      sha = j.sha;
    }
    const put = await fetch(api, {
      method: 'PUT',
      headers,
      body: JSON.stringify({
        message: '发布文章：' + t,
        content: Buffer.from(md, 'utf8').toString('base64'),
        branch: 'main',
        ...(sha ? { sha } : {})
      })
    });
    if (!put.ok) {
      return respond(500, { ok: false, error: '提交到 GitHub 失败（' + put.status + '），请稍后再试或联系管理员。' });
    }
    return respond(200, { ok: true, message: '发布成功！网站将在 1-2 分钟后自动更新。' });
  } catch (e) {
    return respond(500, { ok: false, error: '服务器出错：' + String(e) });
  }
};
