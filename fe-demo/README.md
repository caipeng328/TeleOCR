# 文档解析

上传 PDF 或图片调用 OCR 接口，左右双栏对照原文与 Markdown 结果，悬停与点击可在两侧联动定位。

## 环境要求

Node 18 / 20 / 22+（Vite 6 的要求）。

## 安装

```bash
npm install
```

## 运行

```bash
npm run dev
```

打包构建：

```bash
npm run build      # 类型检查 + 构建到 dist/
npm run preview    # 本地预览构建产物，http://localhost:4173/pdf/
```

预览地址带 `/pdf/` 是因为生产构建的 `base` 就是它（见下方「部署」）。

## 配置

于 [`ocr.config.ts`](ocr.config.ts) 配置 url（请配置服务器 cors）：

```ts
export const inferApi = {
  protocol: 'http',
  host: '0.0.0.0',
  port: 9090,
  path: '/infer',
} as const;
```

## 部署

构建产物默认挂在 `/pdf/` 路径下（见 `vite.config.ts` 的 `base`）。`deploy/` 下有 Caddy 与 nginx 的示例，它们只负责托管静态文件——接口由浏览器直连，不需要反向代理。
