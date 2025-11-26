import { useQuery } from "@tanstack/react-query";
import { httpClient } from "./httpClient";

export interface FilamentPreset {
    id: number;
    user_id: number;
    name: string;
}

export function useGetFilamentPresets() {
    return useQuery<FilamentPreset[]>({
        queryKey: ["filament-presets"],
        queryFn: async () => {
            const response = await httpClient.get("/filament-preset");
            return response.data;
        },
    });
}
