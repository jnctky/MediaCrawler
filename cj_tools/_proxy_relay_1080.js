// 临时救急中继：127.0.0.1:1080  -->  127.0.0.1:10808 (v2rayN/xray SOCKS5)
// 用途：当前运行的 WorkBuddy 客户端进程仍缓存着旧环境变量 all_proxy=127.0.0.1:1080，
//       而 1080 已无人监听。此中继让 1080 重新可连，从而让资料库上传先跑通。
// 说明：纯 TCP 透传，不解析协议；客户端发来的 SOCKS5 握手会原样转给 xray。
// 用完即可删除本文件并结束进程。客户端重启后不再需要它。
const net = require('net');

const LISTEN_HOST = '127.0.0.1';
const LISTEN_PORT = 1080;
const TARGET_HOST = '127.0.0.1';
const TARGET_PORT = 10808;

const server = net.createServer((client) => {
  const upstream = net.connect(TARGET_PORT, TARGET_HOST);
  client.pipe(upstream);
  upstream.pipe(client);
  const cleanup = () => { client.destroy(); upstream.destroy(); };
  client.on('error', cleanup);
  upstream.on('error', cleanup);
  client.on('close', cleanup);
  upstream.on('close', cleanup);
});

server.on('error', (e) => {
  console.error('[relay] listen error:', e.message);
  process.exit(1);
});

server.listen(LISTEN_PORT, LISTEN_HOST, () => {
  console.log(`[relay] ${LISTEN_HOST}:${LISTEN_PORT} -> ${TARGET_HOST}:${TARGET_PORT} 已就绪`);
});
