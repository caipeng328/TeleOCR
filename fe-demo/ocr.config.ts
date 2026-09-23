
export const inferApi = {
  protocol: 'http',
  host: '127.0.0.1',
  port: 9090,
  /** 接口路径 */
  path: '/infer',
} as const;

/** 完整接口地址，如 http://127.0.0.1:9090/infer */
export const inferApiUrl = `${inferApi.protocol}://${inferApi.host}:${inferApi.port}${inferApi.path}`;
