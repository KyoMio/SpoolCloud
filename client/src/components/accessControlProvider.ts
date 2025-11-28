import { AccessControlProvider } from "@refinedev/core";
import { authProvider } from "../authProvider";

export const accessControlProvider: AccessControlProvider = {
    can: async ({ resource, action }) => {
        if (resource === "settings") {
            const role = await authProvider.getPermissions?.();
            if (role === "admin") {
                return { can: true };
            }
            return {
                can: false,
                reason: "Only administrators can access settings",
            };
        }

        return { can: true };
    },
};
