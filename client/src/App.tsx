import { Authenticated, Refine } from "@refinedev/core";
import { RefineKbar, RefineKbarProvider } from "@refinedev/kbar";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";

import { AuthPage, ErrorComponent } from "@refinedev/antd";
import "@refinedev/antd/dist/reset.css";

import {
    FileOutlined,
    HighlightOutlined,
    HomeOutlined,
    QuestionOutlined,
    TableOutlined,
    ToolOutlined,
    UserOutlined,
} from "@ant-design/icons";
import loadable from "@loadable/component";
import routerBindings, { CatchAllNavigate, DocumentTitleHandler, UnsavedChangesNotifier } from "@refinedev/react-router";
import { ConfigProvider } from "antd";
import { Locale } from "antd/es/locale";
import axios from "axios";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { BrowserRouter, Outlet, Route, Routes } from "react-router";
import { TOKEN_KEY, authProvider } from "./authProvider";
import dataProvider from "./components/dataProvider";
import { Favicon } from "./components/favicon";
import { SpoolCloudLayout } from "./components/layout";
import liveProvider from "./components/liveProvider";
import SpoolCloudNotificationProvider from "./components/notificationProvider";
import { ColorModeContextProvider } from "./contexts/color-mode";
import { languages } from "./i18n";
import { ProfilePage } from "./pages/profile";
import { NotificationsPage } from "./pages/notifications";
import { LoginPage } from "./pages/login";
import { RegisterPage } from "./pages/register";
import { getAPIURL, getBasePath } from "./utils/url";

interface ResourcePageProps {
    resource: "spools" | "filaments" | "vendors";
    page: "list" | "create" | "edit" | "show";
    mode?: "create" | "clone";
}

const LoadableResourcePage = loadable(
    (props: ResourcePageProps) => import(`./pages/${props.resource}/${props.page}.tsx`),
    {
        fallback: <div>Page is Loading...</div>,
        cacheKey: (props: ResourcePageProps) => `${props.resource}-${props.page}-${props.mode ?? ""}`,
    }
);

interface LoadablePageProps {
    name: string;
}

const LoadablePage = loadable((props: LoadablePageProps) => import(`./pages/${props.name}/index.tsx`), {
    fallback: <div>Page is Loading...</div>,
    cacheKey: (props: LoadablePageProps) => `page-${props.name}`,
});

function App() {
    const { t, i18n } = useTranslation();

    const i18nProvider = {
        translate: (key: string, params?: never) => t(key, params),
        changeLocale: (lang: string) => i18n.changeLanguage(lang),
        getLocale: () => i18n.language,
    };

    // Fetch the antd locale using dynamic imports
    const [antdLocale, setAntdLocale] = useState<Locale | undefined>();
    useEffect(() => {
        const fetchLocale = async () => {
            const locale = await import(
                `./../node_modules/antd/es/locale/${languages[i18n.language].fullCode.replace("-", "_")}.js`
            );
            setAntdLocale(locale.default);
        };
        fetchLocale().catch(console.error);
    }, [i18n.language]);

    const axiosInstance = axios.create();

    axiosInstance.interceptors.request.use((request) => {
        const token = localStorage.getItem(TOKEN_KEY);
        if (token && request.headers) {
            request.headers["Authorization"] = `Bearer ${token}`;
        }
        return request;
    });



    return (
        <BrowserRouter basename={getBasePath() + "/"}>
            <RefineKbarProvider>
                <ColorModeContextProvider>
                    <ConfigProvider
                        locale={antdLocale}
                        theme={{
                            token: {
                                colorPrimary: "#dc7734",
                            },
                        }}
                    >
                        <Refine
                            dataProvider={dataProvider(getAPIURL(), axiosInstance)}
                            notificationProvider={SpoolCloudNotificationProvider}
                            authProvider={authProvider}
                            i18nProvider={i18nProvider}
                            routerProvider={routerBindings}
                            liveProvider={liveProvider(getAPIURL())}
                            resources={[
                                {
                                    name: "home",
                                    list: "/",
                                    meta: {
                                        canDelete: false,
                                        icon: <HomeOutlined />,
                                    },
                                },
                                {
                                    name: "spool",
                                    list: "/spool",
                                    create: "/spool/create",
                                    clone: "/spool/clone/:id",
                                    edit: "/spool/edit/:id",
                                    show: "/spool/show/:id",
                                    meta: {
                                        canDelete: true,
                                        icon: <FileOutlined />,
                                    },
                                },
                                {
                                    name: "filament",
                                    list: "/filament",
                                    create: "/filament/create",
                                    clone: "/filament/clone/:id",
                                    edit: "/filament/edit/:id",
                                    show: "/filament/show/:id",
                                    meta: {
                                        canDelete: true,
                                        icon: <HighlightOutlined />,
                                    },
                                },
                                {
                                    name: "vendor",
                                    list: "/vendor",
                                    create: "/vendor/create",
                                    clone: "/vendor/clone/:id",
                                    edit: "/vendor/edit/:id",
                                    show: "/vendor/show/:id",
                                    meta: {
                                        canDelete: true,
                                        icon: <UserOutlined />,
                                    },
                                },
                                {
                                    name: "locations",
                                    list: "/locations",
                                    meta: {
                                        canDelete: false,
                                        icon: <TableOutlined />,
                                    },
                                },
                                {
                                    name: "settings",
                                    list: "/settings",
                                    meta: {
                                        canDelete: false,
                                        icon: <ToolOutlined />,
                                    },
                                },
                                {
                                    name: "help",
                                    list: "/help",
                                    meta: {
                                        canDelete: false,
                                        icon: <QuestionOutlined />,
                                    },
                                },
                            ]}
                            options={{
                                syncWithLocation: true,
                                warnWhenUnsavedChanges: true,
                                disableTelemetry: true,
                            }}
                        >
                            <Routes>
                                <Route
                                    element={
                                        <Authenticated
                                            key="authenticated-inner"
                                            fallback={<CatchAllNavigate to="/login" />}
                                        >
                                            <SpoolCloudLayout>
                                                <Outlet />
                                            </SpoolCloudLayout>
                                        </Authenticated>
                                    }
                                >
                                    <Route index element={<LoadablePage name="home" />} />
                                    <Route path="/spool">
                                        <Route index element={<LoadableResourcePage resource="spools" page="list" />} />
                                        <Route
                                            path="create"
                                            element={<LoadableResourcePage resource="spools" page="create" mode="create" />}
                                        />
                                        <Route
                                            path="clone/:id"
                                            element={<LoadableResourcePage resource="spools" page="create" mode="clone" />}
                                        />
                                        <Route path="edit/:id" element={<LoadableResourcePage resource="spools" page="edit" />} />
                                        <Route path="show/:id" element={<LoadableResourcePage resource="spools" page="show" />} />
                                        <Route path="print" element={<LoadablePage name="printing" />} />
                                    </Route>
                                    <Route path="/filament">
                                        <Route index element={<LoadableResourcePage resource="filaments" page="list" />} />
                                        <Route
                                            path="create"
                                            element={<LoadableResourcePage resource="filaments" page="create" mode="create" />}
                                        />
                                        <Route
                                            path="clone/:id"
                                            element={<LoadableResourcePage resource="filaments" page="create" mode="clone" />}
                                        />
                                        <Route path="edit/:id" element={<LoadableResourcePage resource="filaments" page="edit" />} />
                                        <Route path="show/:id" element={<LoadableResourcePage resource="filaments" page="show" />} />
                                    </Route>
                                    <Route path="/vendor">
                                        <Route index element={<LoadableResourcePage resource="vendors" page="list" />} />
                                        <Route
                                            path="create"
                                            element={<LoadableResourcePage resource="vendors" page="create" mode="create" />}
                                        />
                                        <Route
                                            path="clone/:id"
                                            element={<LoadableResourcePage resource="vendors" page="create" mode="clone" />}
                                        />
                                        <Route path="edit/:id" element={<LoadableResourcePage resource="vendors" page="edit" />} />
                                        <Route path="show/:id" element={<LoadableResourcePage resource="vendors" page="show" />} />
                                    </Route>
                                    <Route path="/settings/*" element={<LoadablePage name="settings" />} />
                                    <Route path="/help" element={<LoadablePage name="help" />} />
                                    <Route path="/locations" element={<LoadablePage name="locations" />} />
                                    <Route path="/profile" element={<ProfilePage />} />
                                    <Route path="/notifications" element={<NotificationsPage />} />
                                    <Route path="*" element={<ErrorComponent />} />
                                </Route>
                                <Route
                                    element={
                                        <Outlet />
                                    }
                                >
                                    <Route path="/login" element={<LoginPage />} />
                                    <Route path="/register" element={<RegisterPage />} />
                                </Route>
                            </Routes>

                            <RefineKbar />
                            <UnsavedChangesNotifier />
                            <DocumentTitleHandler />
                            <ReactQueryDevtools />
                            <Favicon url={getBasePath() + "/favicon.svg"} />
                        </Refine>
                    </ConfigProvider>
                </ColorModeContextProvider>
            </RefineKbarProvider>
        </BrowserRouter>
    );
}

export default App;
