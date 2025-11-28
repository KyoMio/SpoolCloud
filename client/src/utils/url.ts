declare global {
    interface Window {
        SPOOLCLOUD_BASE_PATH: string;
    }
}

/**
 * Returns the base path of the application.
 *
 * If a base path is set, this returns e.g. "/spoolcloud". If none is set, it returns "".
 *
 * @return {string} The base path of the application. If the `SPOOLCLOUD_BASE_PATH`
 * window variable is set and not empty, it is returned. Otherwise, the
 * default base path "" is returned.
 */
export function getBasePath(): string {
    if (window.SPOOLCLOUD_BASE_PATH && window.SPOOLCLOUD_BASE_PATH.length > 0) {
        return window.SPOOLCLOUD_BASE_PATH;
    } else {
        return "";
    }
}

/**
 * A function that returns the SpoolCloud API URL
 * This returns e.g. "/spoolcloud/api/v1" if the base path is "/spoolcloud"
 *
 * @return {string} The API URL
 */
export function getAPIURL(): string {
    const apiURL = import.meta.env.VITE_APIURL || "/api/v1";
    return getBasePath() + apiURL;
}
