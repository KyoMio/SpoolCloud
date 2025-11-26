import { useLogin, useGetLocale, useSetLocale } from "@refinedev/core";
import { Button, Card, Form, Input, Layout, Typography, theme, Dropdown, MenuProps } from "antd";
import { DownOutlined, GlobalOutlined } from "@ant-design/icons";
import React from "react";
import { useTranslation } from "react-i18next";
import { languages } from "../../i18n";

const { Title } = Typography;
const { useToken } = theme;

export const LoginPage: React.FC = () => {
    const { token } = useToken();
    const { mutate: login, isLoading } = useLogin();
    const { t } = useTranslation();
    const locale = useGetLocale();
    const changeLanguage = useSetLocale();

    const currentLocale = locale();

    const languageMenuItems: MenuProps["items"] = [...(Object.keys(languages) || [])].sort().map((lang: string) => ({
        key: lang,
        onClick: () => changeLanguage(lang),
        label: languages[lang].name,
    }));

    const onFinish = (values: any) => {
        login(values);
    };

    return (
        <Layout
            style={{
                height: "100vh",
                justifyContent: "center",
                alignItems: "center",
                backgroundColor: token.colorBgContainer,
            }}
        >
            <div style={{ position: "absolute", top: "20px", right: "20px" }}>
                <Dropdown menu={{ items: languageMenuItems }}>
                    <Button icon={<GlobalOutlined />}>
                        {languages[currentLocale]?.name || "Language"} <DownOutlined />
                    </Button>
                </Dropdown>
            </div>
            <Card
                style={{
                    width: "100%",
                    maxWidth: "400px",
                    padding: "24px",
                }}
            >
                <div style={{ textAlign: "center", marginBottom: "24px" }}>
                    <img src="/icons/spoolcloud.svg" alt="SpoolCloud" style={{ height: "48px", marginBottom: "16px" }} />
                    <Title level={3}>{t("pages.login.title", "Sign in to SpoolCloud")}</Title>
                </div>

                <Form
                    layout="vertical"
                    onFinish={onFinish}
                    initialValues={{
                        username: "admin",
                        password: "admin",
                    }}
                >
                    <Form.Item
                        label={t("pages.login.fields.username", "Username")}
                        name="username"
                        rules={[
                            {
                                required: true,
                                message: t("pages.login.errors.requiredUsername", "Please enter your username"),
                            },
                        ]}
                    >
                        <Input size="large" />
                    </Form.Item>

                    <Form.Item
                        label={t("pages.login.fields.password", "Password")}
                        name="password"
                        rules={[
                            {
                                required: true,
                                message: t("pages.login.errors.requiredPassword", "Please enter your password"),
                            },
                        ]}
                    >
                        <Input.Password size="large" />
                    </Form.Item>

                    <Form.Item>
                        <Button
                            type="primary"
                            htmlType="submit"
                            size="large"
                            block
                            loading={isLoading}
                        >
                            {t("pages.login.buttons.submit", "Sign in")}
                        </Button>
                    </Form.Item>

                    <div style={{ textAlign: "center", marginTop: "16px" }}>
                        <Typography.Text type="secondary">
                            {t("pages.login.noAccount", "Don't have an account?")}{" "}
                            <a href="/register">{t("pages.login.register", "Sign up")}</a>
                        </Typography.Text>
                    </div>
                </Form>
            </Card>
        </Layout>
    );
};
