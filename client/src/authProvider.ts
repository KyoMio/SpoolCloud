import { AuthProvider } from "@refinedev/core";
import axios from "axios";
import { getAPIURL } from "./utils/url";

export const TOKEN_KEY = "spoolcloud_auth_token";

export const authProvider: AuthProvider = {
  login: async ({ username, password }) => {
    try {
      const formData = new FormData();
      formData.append("username", username);
      formData.append("password", password);

      const { data } = await axios.post(`${getAPIURL()}/auth/token`, formData, {
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
      });

      if (data.access_token) {
        localStorage.setItem(TOKEN_KEY, data.access_token);
        return {
          success: true,
          redirectTo: "/",
        };
      }
    } catch (error) {
      return {
        success: false,
        error: {
          name: "LoginError",
          message: "Invalid username or password",
        },
      };
    }
    return {
      success: false,
      error: {
        name: "LoginError",
        message: "Invalid username or password",
      },
    };
  },
  logout: async () => {
    localStorage.removeItem(TOKEN_KEY);
    return {
      success: true,
      redirectTo: "/login",
    };
  },
  check: async () => {
    const token = localStorage.getItem(TOKEN_KEY);
    if (token) {
      return {
        authenticated: true,
      };
    }

    return {
      authenticated: false,
      redirectTo: "/login",
    };
  },
  getPermissions: async () => {
    const token = localStorage.getItem(TOKEN_KEY);
    if (!token) return null;

    try {
      // We could decode the token here if it contains role, or fetch from /auth/me
      // For now, let's fetch from /auth/me
      const { data } = await axios.get(`${getAPIURL()}/auth/me`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      return data.role;
    } catch (error) {
      return null;
    }
  },
  getIdentity: async () => {
    const token = localStorage.getItem(TOKEN_KEY);
    if (!token) return null;

    try {
      const { data } = await axios.get(`${getAPIURL()}/auth/me`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      return {
        id: data.id,
        name: data.username,
        avatar: "https://i.pravatar.cc/150", // Placeholder
      };
    } catch (error) {
      return null;
    }
  },
  onError: async (error) => {
    if (error.response?.status === 401) {
      return {
        logout: true,
      };
    }

    return { error };
  },
  register: async ({ username, password, invite_code }) => {
    try {
      await axios.post(`${getAPIURL()}/auth/register`, {
        username,
        password,
        invite_code,
      });
      return {
        success: true,
        redirectTo: "/login",
      };
    } catch (error) {
      return {
        success: false,
        error: {
          name: "RegisterError",
          message: "Registration failed",
        },
      };
    }
  },
};
