import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [sveltekit()],
	server: {
		proxy: {
			// 将所有 /api 开头的请求代理到后端服务
			'/api': {
				target: 'http://127.0.0.1:8000',
				changeOrigin: true,
			},
			// Proxy static assets served by FastAPI
			'/static': {
				target: 'http://127.0.0.1:8000',
				changeOrigin: true,
			}
		}
	}
});
