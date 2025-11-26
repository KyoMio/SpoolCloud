import axios from "axios";
import { TOKEN_KEY } from "../authProvider";
import { getAPIURL } from "./url";

/**
 * Shared axios instance with authentication interceptor
 */
export const httpClient = axios.create({
    baseURL: getAPIURL(),
});

// Add auth token to all requests
httpClient.interceptors.request.use((config) => {
    const token = localStorage.getItem(TOKEN_KEY);
    if (token && config.headers) {
        config.headers["Authorization"] = `Bearer ${token}`;
    }
    return config;
});
