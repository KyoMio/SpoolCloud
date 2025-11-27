import { BellOutlined, SettingOutlined, SendOutlined, CheckOutlined, DeleteOutlined } from "@ant-design/icons";
import { useCustom, useCustomMutation, useInvalidate, useList } from "@refinedev/core";
import {
    Button,
    Card,
    Form,
    Input,
    InputNumber,
    List,
    message,
    Select,
    Space,
    Spin,
    Switch,
    Tabs,
    Tag,
    Typography,
} from "antd";
import React, { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { getAPIURL } from "../../utils/url";
import { TOKEN_KEY } from "../../authProvider";

import { PresetReplaceModal } from "../../components/presetReplaceModal";

const { Title, Text } = Typography;

interface Notification {
    id: number;
    title: string;
    message: string;
    type: string;
    is_read: boolean;
    created_at: string;
    data?: Record<string, any>;
}

interface NotificationConfig {
    id: number;
    channel: string;
    webhook_url?: string;
    config_data?: Record<string, any>;
    is_enabled: boolean;
}

export const NotificationsPage: React.FC = () => {
    const { t } = useTranslation();
    const [form] = Form.useForm();
    const invalidate = useInvalidate();
    const [selectedChannel, setSelectedChannel] = useState<string>("serverchan");

    const { data: notificationsData, isLoading: isLoadingNotifications } = useList<Notification>({
        resource: "notification",
        pagination: { mode: "off" },
        sorters: [
            {
                field: "created_at",
                order: "desc",
            },
        ],
    });

    const { data: configData, isLoading: isLoadingConfig } = useCustom({
        url: `${getAPIURL()}/notification/config`,
        method: "get",
        config: {
            headers: {
                Authorization: `Bearer ${localStorage.getItem(TOKEN_KEY)}`
            }
        }
    });

    useEffect(() => {
        if (configData?.data) {
            const config = configData.data as NotificationConfig;
            setSelectedChannel(config.channel);
            form.setFieldsValue({
                is_enabled: config.is_enabled,
                channel: config.channel,
                webhook_url: config.webhook_url,
                ...config.config_data,
            });
        }
    }, [configData, form]);

    const { mutateAsync: markAsReadMutation } = useCustomMutation();
    const { mutateAsync: markAllAsReadMutation } = useCustomMutation();
    const { mutateAsync: deleteNotificationMutation } = useCustomMutation();
    const { mutateAsync: updateConfigMutation } = useCustomMutation();
    const [isUpdatingConfig, setIsUpdatingConfig] = useState(false);
    const [isTestingNotification, setIsTestingNotification] = useState(false);

    const handleMarkAsRead = async (id: number) => {
        await markAsReadMutation({
            url: `${getAPIURL()}/notification/${id}/read`,
            method: "put",
            values: {},
            config: {
                headers: {
                    Authorization: `Bearer ${localStorage.getItem(TOKEN_KEY)}`
                }
            }
        });
        invalidate({ resource: "notification", invalidates: ["list"] });
    };

    const handleMarkAllAsRead = async () => {
        await markAllAsReadMutation({
            url: `${getAPIURL()}/notification/read-all`,
            method: "put",
            values: {},
            config: {
                headers: {
                    Authorization: `Bearer ${localStorage.getItem(TOKEN_KEY)}`
                }
            }
        });
        invalidate({ resource: "notification", invalidates: ["list"] });
        message.success(t("notificationsPage.list.markAllReadSuccess") || "All notifications marked as read");
    };

    const handleDelete = async (id: number) => {
        await deleteNotificationMutation({
            url: `${getAPIURL()}/notification/${id}`,
            method: "delete",
            values: {},
            config: {
                headers: {
                    Authorization: `Bearer ${localStorage.getItem(TOKEN_KEY)}`
                }
            }
        });
        invalidate({ resource: "notification", invalidates: ["list"] });
        message.success(t("notifications.deleteSuccess", { resource: "Notification" }));
    };

    const handleConfigFinish = async (values: any) => {
        setIsUpdatingConfig(true);
        try {
            const config_data: Record<string, any> = {};

            // Extract channel-specific config
            if (values.channel === "bark") {
                config_data.base_url = values.base_url;
                config_data.device_key = values.device_key;
            }

            await updateConfigMutation({
                url: `${getAPIURL()}/notification/config`,
                method: "put",
                values: {
                    channel: values.channel,
                    webhook_url: values.webhook_url || null,
                    config_data: Object.keys(config_data).length > 0 ? config_data : null,
                    is_enabled: values.is_enabled,
                },
                config: {
                    headers: {
                        Authorization: `Bearer ${localStorage.getItem(TOKEN_KEY)}`
                    }
                }
            });
            message.success(t("notificationsPage.config.saveSuccess"));
            invalidate({ resource: "notification/config", invalidates: ["all"] });
        } catch (error) {
            console.error(error);
            message.error(t("notificationsPage.config.saveError"));
        } finally {
            setIsUpdatingConfig(false);
        }
    };

    const handleTestNotification = async () => {
        setIsTestingNotification(true);
        try {
            await updateConfigMutation({
                url: `${getAPIURL()}/notification/test`,
                method: "post",
                values: {},
                config: {
                    headers: {
                        Authorization: `Bearer ${localStorage.getItem(TOKEN_KEY)}`
                    }
                }
            });
            message.success(t("notificationsPage.config.testSuccess"));
        } catch (error: any) {
            const errorMsg = error?.response?.data?.message || t("notificationsPage.config.testError");
            message.error(errorMsg);
        } finally {
            setIsTestingNotification(false);
        }
    };

    const renderChannelFields = () => {
        switch (selectedChannel) {
            case "serverchan":
                return (
                    <Form.Item
                        name="webhook_url"
                        label={t("notificationsPage.config.apiKey")}
                        rules={[{ required: true, message: t("notificationsPage.config.apiKeyRequired") }]}
                    >
                        <Input placeholder="SCT..." />
                    </Form.Item>
                );

            case "bark":
                return (
                    <>
                        <Form.Item
                            name="base_url"
                            label={t("notificationsPage.config.baseUrl")}
                            rules={[{ required: true, message: t("notificationsPage.config.baseUrlRequired") }]}
                        >
                            <Input placeholder="https://api.day.app" />
                        </Form.Item>
                        <Form.Item
                            name="device_key"
                            label={t("notificationsPage.config.deviceKey")}
                            rules={[{ required: true, message: t("notificationsPage.config.deviceKeyRequired") }]}
                        >
                            <Input placeholder="your_device_key" />
                        </Form.Item>
                    </>
                );

            case "synochat":
                return (
                    <Form.Item
                        name="webhook_url"
                        label={t("notificationsPage.config.webhookUrl")}
                        rules={[{ required: true, message: t("notificationsPage.config.webhookUrlRequired") }]}
                    >
                        <Input placeholder="https://..." />
                    </Form.Item>
                );

            case "email":
                return (
                    <>
                        <Form.Item
                            name="smtp_server"
                            label={t("notificationsPage.config.smtpServer")}
                            rules={[{ required: true }]}
                        >
                            <Input placeholder="smtp.gmail.com" />
                        </Form.Item>
                        <Form.Item
                            name="smtp_port"
                            label={t("notificationsPage.config.smtpPort")}
                            rules={[{ required: true }]}
                            initialValue={587}
                        >
                            <InputNumber min={1} max={65535} style={{ width: "100%" }} />
                        </Form.Item>
                        <Form.Item
                            name="email"
                            label={t("notificationsPage.config.email")}
                            rules={[{ required: true, type: "email" }]}
                        >
                            <Input placeholder="your@email.com" />
                        </Form.Item>
                        <Form.Item
                            name="password"
                            label={t("notificationsPage.config.password")}
                            rules={[{ required: true }]}
                        >
                            <Input.Password />
                        </Form.Item>
                        <Form.Item
                            name="email_to"
                            label={t("notificationsPage.config.emailTo")}
                        >
                            <Input placeholder={t("notificationsPage.config.emailToPlaceholder")} />
                        </Form.Item>
                    </>
                );

            case "webhook":
                return (
                    <>
                        <Form.Item
                            name="webhook_url"
                            label={t("notificationsPage.config.webhookUrl")}
                            rules={[{ required: true }]}
                        >
                            <Input placeholder="https://..." />
                        </Form.Item>
                        <Form.Item
                            name="headers"
                            label={t("notificationsPage.config.headers")}
                        >
                            <Input.TextArea
                                placeholder='{"Content-Type": "application/json"}'
                                rows={3}
                            />
                        </Form.Item>
                    </>
                );

            default:
                return null;
        }
    };

    const [replaceModalOpen, setReplaceModalOpen] = useState(false);
    const [replacePresetId, setReplacePresetId] = useState<number | null>(null);
    const [replaceNotificationId, setReplaceNotificationId] = useState<number | null>(null);

    const handleResolveConflict = (notification: Notification) => {
        if (notification.data?.preset_id) {
            setReplacePresetId(notification.data.preset_id);
            setReplaceNotificationId(notification.id);
            setReplaceModalOpen(true);
        }
    };

    const handleReplaceSuccess = async () => {
        if (replaceNotificationId) {
            await handleDelete(replaceNotificationId);
        }
        invalidate({ resource: "filament-preset", invalidates: ["list"] });
    };

    const notificationsList = (
        <Card>
            <Space direction="vertical" style={{ width: "100%" }}>
                <Space>
                    <Title level={4}>
                        {t("notificationsPage.tabs.list")}
                    </Title>
                    <Button onClick={handleMarkAllAsRead} size="small" icon={<CheckOutlined />}>
                        {t("notificationsPage.list.markAllRead")}
                    </Button>
                </Space>

                <List
                    dataSource={notificationsData?.data || []}
                    locale={{ emptyText: t("notificationsPage.list.empty") }}
                    renderItem={(item) => (
                        <List.Item
                            actions={[
                                item.type === "warning" && item.data?.action === "replace_preset" && (
                                    <Button
                                        size="small"
                                        type="primary"
                                        onClick={() => handleResolveConflict(item)}
                                    >
                                        {t("notifications.resolve", "Resolve")}
                                    </Button>
                                ),
                                !item.is_read && (
                                    <Button size="small" onClick={() => handleMarkAsRead(item.id)} icon={<CheckOutlined />}>
                                        {t("notificationsPage.list.markRead")}
                                    </Button>
                                ),
                                <Button
                                    size="small"
                                    danger
                                    onClick={() => handleDelete(item.id)}
                                    icon={<DeleteOutlined />}
                                >
                                    {t("notificationsPage.list.delete")}
                                </Button>,
                            ].filter(Boolean)}
                        >
                            <List.Item.Meta
                                title={
                                    <Space>
                                        {item.title}
                                        {!item.is_read && <Tag color="blue">{t("notificationsPage.list.unread")}</Tag>}
                                        {item.type === "warning" && <Tag color="orange">{t("notifications.types.warning", "Warning")}</Tag>}
                                    </Space>
                                }
                                description={
                                    <>
                                        <Text>{item.message}</Text>
                                        <br />
                                        <Text type="secondary" style={{ fontSize: "12px" }}>
                                            {new Date(item.created_at).toLocaleString()}
                                        </Text>
                                    </>
                                }
                            />
                        </List.Item>
                    )}
                />
            </Space>
            {replacePresetId && (
                <PresetReplaceModal
                    isOpen={replaceModalOpen}
                    onClose={() => setReplaceModalOpen(false)}
                    presetId={replacePresetId}
                    notificationId={replaceNotificationId || undefined}
                    onSuccess={handleReplaceSuccess}
                />
            )}
        </Card>
    );

    const configForm = (
        <Card
            title={
                <Space>
                    <SettingOutlined />
                    {t("notificationsPage.tabs.config")}
                </Space>
            }
        >
            {isLoadingConfig ? (
                <Spin />
            ) : (
                <Form
                    form={form}
                    layout="vertical"
                    onFinish={handleConfigFinish}
                    initialValues={{ is_enabled: true, channel: "serverchan" }}
                >
                    <Form.Item
                        name="is_enabled"
                        label={t("notificationsPage.config.isEnabled")}
                        valuePropName="checked"
                    >
                        <Switch />
                    </Form.Item>

                    <Form.Item
                        name="channel"
                        label={t("notificationsPage.config.channel")}
                        rules={[{ required: true }]}
                    >
                        <Select onChange={(value) => setSelectedChannel(value)}>
                            <Select.Option value="serverchan">ServerChan</Select.Option>
                            <Select.Option value="bark">Bark</Select.Option>
                            <Select.Option value="synochat">Synology Chat</Select.Option>
                        </Select>
                    </Form.Item>

                    {renderChannelFields()}

                    <Form.Item>
                        <Space>
                            <Button type="primary" htmlType="submit" loading={isUpdatingConfig}>
                                {t("notificationsPage.config.save")}
                            </Button>
                            <Button
                                icon={<SendOutlined />}
                                onClick={handleTestNotification}
                                loading={isTestingNotification}
                            >
                                {t("notificationsPage.config.testNotification")}
                            </Button>
                        </Space>
                    </Form.Item>
                </Form>
            )}
        </Card>
    );

    return (
        <div style={{ padding: "24px" }}>
            <Title level={2}>{t("notificationsPage.title")}</Title>
            <Tabs
                defaultActiveKey="list"
                items={[
                    {
                        key: "list",
                        label: (
                            <span>
                                <BellOutlined />
                                {t("notificationsPage.tabs.list")}
                            </span>
                        ),
                        children: notificationsList,
                    },
                    {
                        key: "config",
                        label: (
                            <span>
                                <SettingOutlined />
                                {t("notificationsPage.tabs.config")}
                            </span>
                        ),
                        children: configForm,
                    },
                ]}
            />
        </div>
    );
};
