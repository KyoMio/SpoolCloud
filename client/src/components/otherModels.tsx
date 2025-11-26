import { useQuery } from "@tanstack/react-query";
import { Tooltip } from "antd";
import { ColumnFilterItem } from "antd/es/table/interface";
import { IFilament } from "../pages/filaments/model";
import { IVendor } from "../pages/vendors/model";
import { httpClient } from "../utils/httpClient";

export function useSpoolCloudFilamentFilter(enabled: boolean = false) {
  return useQuery<IFilament[], unknown, ColumnFilterItem[]>({
    enabled: enabled,
    queryKey: ["filaments"],
    queryFn: async () => {
      const response = await httpClient.get("/filament");
      return response.data;
    },
    select: (data) => {
      // Concatenate vendor name and filament name
      const names = data
        // Remove empty names
        .filter((filament) => {
          return filament.name !== null && filament.name !== undefined && filament.name !== "";
        })
        // Transform to ColumnFilterItem
        .map((filament) => {
          let name = "";
          if (filament.vendor?.name) {
            name = `${filament.vendor.name} - ${filament.name ?? "<unknown>"}`;
          } else {
            name = `${filament.name ?? "<unknown>"}`;
          }

          const tooltipParts: React.ReactNode[] = [];
          if (filament.color_hex) {
            tooltipParts.push(
              <div
                key="color"
                style={{
                  borderRadius: ".4em",
                  width: "1.4em",
                  height: "1.4em",
                  backgroundColor: "#" + filament.color_hex,
                }}
              ></div>
            );
          }
          if (filament.material) {
            tooltipParts.push(<div key="material">{filament.material}</div>);
          }
          if (filament.weight) {
            tooltipParts.push(<div key="weight">{filament.weight}g</div>);
          }

          return {
            text: (
              <Tooltip
                title={
                  <div
                    style={{
                      display: "flex",
                      flexDirection: "row",
                      gap: ".5em",
                      alignContent: "center",
                    }}
                  >
                    {tooltipParts}
                  </div>
                }
              >
                {name}
              </Tooltip>
            ),
            value: filament.id,
            sortId: name,
          };
        })
        // Remove duplicates
        .filter((item, index, self) => self.findIndex((t) => t.value === item.value) === index)
        // Sort by name
        .sort((a, b) => a.sortId.localeCompare(b.sortId));
      return names;
    },
  });
}

export function useSpoolCloudFilamentNames(enabled: boolean = false) {
  return useQuery<IFilament[], unknown, string[]>({
    enabled: enabled,
    queryKey: ["filaments"],
    queryFn: async () => {
      const response = await httpClient.get("/filament");
      return response.data;
    },
    select: (data) => {
      // Concatenate vendor name and filament name
      let names = data
        .filter((filament) => {
          return filament.name !== null && filament.name !== undefined && filament.name !== "";
        })
        .map((filament) => {
          return filament.name ?? "<unknown>";
        })
        .sort();
      // Remove duplicates
      names = [...new Set(names)];
      return names;
    },
  });
}

export function useSpoolCloudVendors(enabled: boolean = false) {
  return useQuery<IVendor[], unknown, string[]>({
    enabled: enabled,
    queryKey: ["vendors"],
    queryFn: async () => {
      const response = await httpClient.get("/vendor");
      return response.data;
    },
    select: (data) => {
      return data
        .map((vendor) => {
          return vendor.name ?? `ID ${vendor.id}`;
        })
        .sort();
    },
  });
}

export function useSpoolCloudMaterials(enabled: boolean = false) {
  return useQuery<string[]>({
    enabled: enabled,
    queryKey: ["materials"],
    queryFn: async () => {
      const response = await httpClient.get("/material");
      return response.data;
    },
    select: (data) => {
      return data.sort();
    },
  });
}

export function useSpoolCloudArticleNumbers(enabled: boolean = false) {
  return useQuery<string[]>({
    enabled: enabled,
    queryKey: ["articleNumbers"],
    queryFn: async () => {
      const response = await httpClient.get("/article-number");
      return response.data;
    },
    select: (data) => {
      return data.sort();
    },
  });
}

export function useSpoolCloudLotNumbers(enabled: boolean = false) {
  return useQuery<string[]>({
    enabled: enabled,
    queryKey: ["lotNumbers"],
    queryFn: async () => {
      const response = await httpClient.get("/lot-number");
      return response.data;
    },
    select: (data) => {
      return data.sort();
    },
  });
}

export function useSpoolCloudLocations(enabled: boolean = false) {
  return useQuery<string[]>({
    enabled: enabled,
    queryKey: ["locations"],
    queryFn: async () => {
      const response = await httpClient.get("/location");
      return response.data;
    },
    select: (data) => {
      return data.sort();
    },
  });
}
