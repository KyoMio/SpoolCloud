import { DeleteOutlined, PlusOutlined, CopyOutlined, UserOutlined } from "@ant-design/icons";
import { useCustomMutation, useList, useNotification, useCustom } from "@refinedev/core";
import {
    Button,
    Card,
    Form,
    Input,
    List,
    Modal,
    Space,
    Tabs,
    Typography,
    Table,
    Tag,
    message,
    Popconfirm,
} from "antd";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { getAPIURL } from "../../utils/url";
import axios from "axios";
import { TOKEN_KEY } from "../../authProvider";

const { Title, Text } = Typography;

export const ProfilePage = () => {
    const { t } = useTranslation();
    const { open } = useNotification();
    const [form] = Form.useForm();
    const [apiKeyForm] = Form.useForm();
    const [isModalVisible, setIsModalVisible] = useState(false);
    const [newApiKey, setNewApiKey] = useState<string | null>(null);
    const [newInviteCode, setNewInviteCode] = useState<string | null>(null);

    // Check if current user is admin
    const { data: currentUserData } = useCustom({
        url: `${getAPIURL()}/auth/me`,
        method: "get",
        config: {
            headers: {
                Authorization: `Bearer ${localStorage.getItem(TOKEN_KEY)}`
            }
        }
    });

    const isAdmin = currentUserData?.data?.is_admin || false;

    const { mutate: changePassword, isLoading: isChangingPassword } = useCustomMutation();

    const handleChangePassword = (values: any) => {
        changePassword(
            {
                url: `${getAPIURL()}/auth/change-password`,
                method: "post",
                values,
                config: {
                    headers: {
                        Authorization: `Bearer ${localStorage.getItem(TOKEN_KEY)}`
                    }
                },
                successNotification: () => {
                    form.resetFields();
                    return {
                        type: "success",
                        message: t("profile.passwordChanged"),
                    };
                },
                errorNotification: (error: any) => {
                    return {
                        type: "error",
                        message: error.response?.data?.message || t("profile.passwordChangeFailed"),
                    };
                },
            }
        );
    };

    const { data: apiKeys, refetch: refetchApiKeys } = useList({
        resource: "auth/api-key",
    });

    const handleCreateApiKey = async (values: { label: string }) => {
        try {
            const { data } = await axios.post(
                `${getAPIURL()}/auth/api-key`,
                values,
                {
                    headers: {
                        Authorization: `Bearer ${localStorage.getItem(TOKEN_KEY)}`
                    }
                }
            );
            setNewApiKey(data.key);
            refetchApiKeys();
            apiKeyForm.resetFields();
        } catch (error) {
            open?.({
                type: "error",
                message: t("profile.apiKeyCreateFailed"),
            });
        }
    };

    const handleDeleteApiKey = async (id: number) => {
        try {
            await axios.delete(`${getAPIURL()}/auth/api-key/${id}`, {
                headers: {
                    Authorization: `Bearer ${localStorage.getItem(TOKEN_KEY)}`
                }
            });
            refetchApiKeys();
            open?.({
                type: "success",
                message: t("profile.apiKeyDeleted"),
            });
        } catch (error) {
            open?.({
                type: "error",
                message: t("profile.apiKeyDeleteFailed"),
            });
        }
    };

    // User Management - Invite Codes
    const { data: inviteCodes, refetch: refetchInviteCodes } = useCustom({
        url: `${getAPIURL()}/invite-code`,
        method: "get",
        config: {
            headers: {
                Authorization: `Bearer ${localStorage.getItem(TOKEN_KEY)}`
            }
        },
        queryOptions: {
            enabled: isAdmin,
        }
    });

    const handleGenerateInviteCode = async () => {
        try {
            const { data } = await axios.post(
                `${getAPIURL()}/invite-code`,
                {},
                {
                    headers: {
                        Authorization: `Bearer ${localStorage.getItem(TOKEN_KEY)}`
                    }
                }
            );
            setNewInviteCode(data.code);
            refetchInviteCodes();
            message.success(t("userManagement.inviteCodeGenerated"));
        } catch (error) {
            message.error(t("userManagement.inviteCodeGenerateFailed"));
        }
    };

    const handleDeleteInviteCode = async (id: number) => {
        try {
            await axios.delete(`${getAPIURL()}/invite-code/${id}`, {
                headers: {
                    Authorization: `Bearer ${localStorage.getItem(TOKEN_KEY)}`
                }
            });
            refetchInviteCodes();
            message.success(t("userManagement.inviteCodeDeleted"));
        } catch (error: any) {
            message.error(error.response?.data?.detail || t("userManagement.inviteCodeDeleteFailed"));
        }
    };

    const handleCopyInviteCode = (code: string) => {
        navigator.clipboard.writeText(code);
        message.success(t("userManagement.inviteCodeCopied"));
    };

    // User Management - Users
    const { data: users, refetch: refetchUsers } = useCustom({
        url: `${getAPIURL()}/admin/users`,
        method: "get",
        config: {
            headers: {
                Authorization: `Bearer ${localStorage.getItem(TOKEN_KEY)}`
            }
        },
        queryOptions: {
            enabled: isAdmin,
        }
    });

    const handleDeleteUser = async (userId: number) => {
        try {
            await axios.delete(`${getAPIURL()}/admin/users/${userId}`, {
                headers: {
                    Authorization: `Bearer ${localStorage.getItem(TOKEN_KEY)}`
                }
            });
            refetchUsers();
            message.success(t("userManagement.userDeleted"));
        } catch (error: any) {
            message.error(error.response?.data?.detail || t("userManagement.userDeleteFailed"));
        }
    };

    const inviteCodeColumns = [
        {
            title: t("userManagement.inviteCode"),
            dataIndex: "code",
            key: "code",
            render: (code: string) => (
                <Space>
                    <Text code>{code}</Text>
                    <Button
                        size="small"
                        icon={<CopyOutlined />}
                        onClick={() => handleCopyInviteCode(code)}
                    />
                </Space>
            ),
        },
        {
            title: t("userManagement.status"),
            dataIndex: "used",
            key: "status",
            render: (used: boolean) => (
                <Tag color={used ? "default" : "green"}>
                    {used ? t("userManagement.used") : t("userManagement.unused")}
                </Tag>
            ),
        },
        {
            title: t("userManagement.usedBy"),
            dataIndex: "used_by_username",
            key: "used_by",
            render: (username: string | null) => username || "-",
        },
        {
            title: t("userManagement.createdAt"),
            dataIndex: "created_at",
            key: "created_at",
            render: (date: string) => new Date(date).toLocaleString(),
        },
        {
            title: t("table.actions"),
            key: "actions",
            render: (_: any, record: any) => (
                !record.used && (
                    <Popconfirm
                        title={t("userManagement.deleteInviteCodeConfirm")}
                        onConfirm={() => handleDeleteInviteCode(record.id)}
                    >
                        <Button danger size="small" icon={<DeleteOutlined />}>
                            {t("buttons.delete")}
                        </Button>
                    </Popconfirm>
                )
            ),
        },
    ];

    const userColumns = [
        {
            title: t("userManagement.username"),
            dataIndex: "username",
            key: "username",
        },
        {
            title: t("userManagement.role"),
            dataIndex: "is_admin",
            key: "role",
            render: (isAdmin: boolean) => (
                <Tag color={isAdmin ? "blue" : "default"}>
                    {isAdmin ? t("userManagement.admin") : t("userManagement.user")}
                </Tag>
            ),
        },
        {
            title: t("userManagement.inviteCodeUsed"),
            dataIndex: "invite_code_used",
            key: "invite_code",
            render: (code: string | null) => code ? <Text code>{code}</Text> : "-",
        },
        {
            title: t("userManagement.createdAt"),
            dataIndex: "created_at",
            key: "created_at",
            render: (date: string) => new Date(date).toLocaleString(),
        },
        {
            title: t("table.actions"),
            key: "actions",
            render: (_: any, record: any) => (
                <Popconfirm
                    title={t("userManagement.deleteUserConfirm")}
                    onConfirm={() => handleDeleteUser(record.id)}
                    disabled={record.id === currentUserData?.data?.id}
                >
                    <Button
                        danger
                        size="small"
                        icon={<DeleteOutlined />}
                        disabled={record.id === currentUserData?.data?.id}
                    >
                        {t("buttons.delete")}
                    </Button>
                </Popconfirm>
            ),
        },
    ];

    const tabItems = [
        {
            key: "general",
            label: t("profile.general"),
            children: (
                <Form
                    form={form}
                    layout="vertical"
                    onFinish={handleChangePassword}
                    style={{ maxWidth: 400 }}
                >
                    <Form.Item
                        label={t("profile.oldPassword")}
                        name="old_password"
                        rules={[{ required: true }]}
                    >
                        <Input.Password />
                    </Form.Item>
                    <Form.Item
                        label={t("profile.newPassword")}
                        name="new_password"
                        rules={[{ required: true, min: 8 }]}
                    >
                        <Input.Password />
                    </Form.Item>
                    <Form.Item>
                        <Button
                            type="primary"
                            htmlType="submit"
                            loading={isChangingPassword}
                        >
                            {t("profile.changePassword")}
                        </Button>
                    </Form.Item>
                </Form>
            ),
        },
        {
            key: "api-keys",
            label: t("profile.apiKeys"),
            children: (
                <Space direction="vertical" style={{ width: "100%" }}>
                    <Button
                        type="primary"
                        icon={<PlusOutlined />}
                        onClick={() => setIsModalVisible(true)}
                    >
                        {t("profile.createApiKey")}
                    </Button>
                    <List
                        dataSource={apiKeys?.data}
                        renderItem={(item: any) => (
                            <List.Item
                                actions={[
                                    <Button
                                        danger
                                        icon={<DeleteOutlined />}
                                        onClick={() => handleDeleteApiKey(item.id)}
                                    >
                                        {t("buttons.delete")}
                                    </Button>,
                                ]}
                            >
                                <List.Item.Meta
                                    title={item.label}
                                    description={`Prefix: ${item.key_prefix} | Created: ${new Date(
                                        item.created_at
                                    ).toLocaleString()}`}
                                />
                            </List.Item>
                        )}
                    />
                </Space>
            ),
        },
    ];

    if (isAdmin) {
        tabItems.push({
            key: "user-management",
            label: (
                <span>
                    <UserOutlined /> {t("userManagement.title")}
                </span>
            ),
            children: (
                <Space direction="vertical" style={{ width: "100%" }} size="large">
                    {/* Invite Code Generator */}
                    <Card title={t("userManagement.inviteCodeGenerator")} size="small">
                        <Space direction="vertical" style={{ width: "100%" }}>
                            <Button
                                type="primary"
                                icon={<PlusOutlined />}
                                onClick={handleGenerateInviteCode}
                            >
                                {t("userManagement.generateInviteCode")}
                            </Button>
                            {newInviteCode && (
                                <Space direction="vertical">
                                    <Text type="secondary">{t("userManagement.newInviteCode")}</Text>
                                    <Space>
                                        <Text code copyable>{newInviteCode}</Text>
                                        <Button
                                            size="small"
                                            onClick={() => setNewInviteCode(null)}
                                        >
                                            {t("buttons.cancel")}
                                        </Button>
                                    </Space>
                                </Space>
                            )}
                        </Space>
                    </Card>

                    {/* Invite Codes List */}
                    <Card title={t("userManagement.inviteCodes")} size="small">
                        <Table
                            dataSource={inviteCodes?.data || []}
                            columns={inviteCodeColumns}
                            rowKey="id"
                            pagination={{ pageSize: 10 }}
                        />
                    </Card>

                    {/* Users List */}
                    <Card title={t("userManagement.users")} size="small">
                        <Table
                            dataSource={users?.data || []}
                            columns={userColumns}
                            rowKey="id"
                            pagination={{ pageSize: 10 }}
                        />
                    </Card>
                </Space>
            ),
        });
    }

    return (
        <Card>
            <Title level={2}>{t("profile.title")}</Title>
            <Tabs items={tabItems} />

            <Modal
                title={t("profile.createApiKey")}
                open={isModalVisible}
                onCancel={() => {
                    setIsModalVisible(false);
                    setNewApiKey(null);
                }}
                footer={null}
            >
                {!newApiKey ? (
                    <Form form={apiKeyForm} onFinish={handleCreateApiKey}>
                        <Form.Item
                            name="label"
                            label={t("profile.apiKeyLabel")}
                            rules={[{ required: true }]}
                        >
                            <Input />
                        </Form.Item>
                        <Button type="primary" htmlType="submit">
                            {t("buttons.create")}
                        </Button>
                    </Form>
                ) : (
                    <Space direction="vertical">
                        <Text type="warning">{t("profile.apiKeyWarning")}</Text>
                        <Text code copyable>{newApiKey}</Text>
                        <Button onClick={() => {
                            setIsModalVisible(false);
                            setNewApiKey(null);
                        }}>{t("buttons.cancel")}</Button>
                    </Space>
                )}
            </Modal>
        </Card>
    );
};
