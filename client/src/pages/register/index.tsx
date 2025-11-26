import { useRegister, useGetLocale, useSetLocale } from "@refinedev/core";
import { Button, Card, Form, Input, Layout, Typography, theme, Dropdown, MenuProps } from "antd";
import { DownOutlined, GlobalOutlined } from "@ant-design/icons";
import React from "react";
import { useTranslation } from "react-i18next";
import { languages } from "../../i18n";

const { Title } = Typography;
const { useToken } = theme;

export const RegisterPage: React.FC = () => {
    const { token } = useToken();
    const { mutate: register, isLoading } = useRegister();
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
        register(values);
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
                    <Title level={3}>{t("pages.register.title", "Sign up for SpoolCloud")}</Title>
                </div>

                <Form
                    layout="vertical"
                    onFinish={onFinish}
                >
                    <Form.Item
                        label={t("pages.register.fields.username", "Username")}
                        name="username"
                        rules={[
                            {
                                required: true,
                                message: t("pages.register.errors.requiredUsername", "Please enter your username"),
                            },
                            {
                                min: 3,
                                message: t("pages.register.errors.usernameMinLength", "Username must be at least 3 characters"),
                            },
                        ]}
                    >
                        <Input size="large" />
                    </Form.Item>

                    <Form.Item
                        label={t("pages.register.fields.inviteCode", "Invite Code")}
                        name="invite_code"
                        rules={[
                            {
                                required: true,
                                message: t("pages.register.errors.requiredInviteCode", "Please enter your invite code"),
                            },
                        ]}
                    >
                        <Input size="large" placeholder={t("pages.register.fields.inviteCodePlaceholder", "Enter invite code")} />
                    </Form.Item>

                    <Form.Item
                        label={t("pages.register.fields.password", "Password")}
                        name="password"
                        rules={[
                            {
                                required: true,
                                message: t("pages.register.errors.requiredPassword", "Please enter your password"),
                            },
                            {
                                min: 8,
                                message: t("pages.register.errors.passwordMinLength", "Password must be at least 8 characters"),
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
                            {t("pages.register.buttons.submit", "Sign up")}
                        </Button>
                    </Form.Item>

                    <div style={{ textAlign: "center", marginTop: "16px" }}>
                        <Typography.Text type="secondary">
                            {t("pages.register.haveAccount", "Already have an account?")}{" "}
                            <a href="/login">{t("pages.register.login", "Sign in")}</a>
                        </Typography.Text>
                    </div>
                </Form>
            </Card>
        </Layout>
    );
};
