import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { httpClient } from "./httpClient";

interface SettingResponseValue {
  value: string;
  is_set: boolean;
  type: string;
}

interface SettingsResponse {
  [key: string]: SettingResponseValue;
}

export function useGetSettings() {
  return useQuery<SettingsResponse>({
    queryKey: ["settings"],
    queryFn: async () => {
      const response = await httpClient.get("/setting/");
      return response.data;
    },
  });
}

export function useGetSetting(key: string) {
  return useQuery<SettingResponseValue>({
    queryKey: ["settings", key],
    queryFn: async () => {
      const response = await httpClient.get(`/setting/${key}`);
      return response.data;
    },
  });
}

export function useSetSetting<T>(key: string) {
  const queryClient = useQueryClient();

  return useMutation<SettingResponseValue, unknown, T, SettingResponseValue | undefined>({
    mutationFn: async (value) => {
      const response = await httpClient.post(`/setting/${key}`, JSON.stringify(value), {
        headers: {
          "Content-Type": "application/json",
        },
      });
      return response.data;
    },
    onMutate: async (value) => {
      await queryClient.cancelQueries(["settings", key]);
      const previousValue = queryClient.getQueryData<SettingResponseValue>(["settings", key]);
      queryClient.setQueryData<SettingResponseValue>(["settings", key], (old) =>
        old ? { ...old, value: JSON.stringify(value) } : undefined
      );
      return previousValue;
    },
    onError: (_error, _value, context) => {
      queryClient.setQueryData<SettingResponseValue>(["settings", key], context);
    },
    onSuccess: (_data, _value) => {
      // Invalidate and refetch
      queryClient.invalidateQueries(["settings", key]);
    },
  });
}
