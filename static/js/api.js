// api.js - Helper for fetch requests

const API = {
    async parseResponse(res) {
        const contentType = res.headers.get('content-type') || '';
        const data = contentType.includes('application/json') ? await res.json() : await res.text();
        if (!res.ok) {
            const detail = typeof data === 'object'
                ? (data.error || data.message || data.detail || JSON.stringify(data))
                : data;
            throw new Error(detail || `HTTP error! status: ${res.status}`);
        }
        return data;
    },

    async get(endpoint, project = null) {
        const headers = {};
        if (project) headers['X-Project'] = project;
        const res = await fetch(endpoint, { headers });
        return await this.parseResponse(res);
    },

    async post(endpoint, data, project = null) {
        const headers = { 'Content-Type': 'application/json' };
        if (project) headers['X-Project'] = project;
        const res = await fetch(endpoint, {
            method: 'POST',
            headers,
            body: JSON.stringify(data)
        });
        return await this.parseResponse(res);
    },

    async put(endpoint, data, project = null) {
        const headers = { 'Content-Type': 'application/json' };
        if (project) headers['X-Project'] = project;
        const res = await fetch(endpoint, {
            method: 'PUT',
            headers,
            body: JSON.stringify(data)
        });
        return await this.parseResponse(res);
    },

    async del(endpoint, project = null, data = null) {
        const headers = {};
        if (project) headers['X-Project'] = project;
        if (data) headers['Content-Type'] = 'application/json';
        const res = await fetch(endpoint, {
            method: 'DELETE',
            headers,
            body: data ? JSON.stringify(data) : undefined
        });
        return await this.parseResponse(res);
    },

    async upload(file, project = null, target = null) {
        const formData = new FormData();
        formData.append('file', file);
        if (target) formData.append('target', target);
        const headers = {};
        if (project) headers['X-Project'] = project;
        
        const res = await fetch('/api/upload', {
            method: 'POST',
            headers,
            body: formData
        });
        return await this.parseResponse(res);
    }
};
