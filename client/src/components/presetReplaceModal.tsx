import { useCustomMutation, useInvalidate, useTranslate } from "@refinedev/core";
import { Form, Modal, Select } from "antd";
import React from "react";
import { useGetFilamentPresets } from "../utils/queryFilamentPresets";

interface PresetReplaceModalProps {
    isOpen: boolean;
    onClose: () => void;
    presetId: number; // The ID of the preset being deleted/replaced
    notificationId?: number; // Optional notification ID to mark as read/delete after success
    onSuccess?: () => void;
}

export const PresetReplaceModal: React.FC<PresetReplaceModalProps> = ({
    isOpen,
    onClose,
    presetId,
    notificationId,
    onSuccess,
}) => {
    const t = useTranslate();
    const [form] = Form.useForm();
    const invalidate = useInvalidate();

    const { mutate: replacePreset, isLoading: isSubmitting } = useCustomMutation();

    const presetsQuery = useGetFilamentPresets();

    // Filter out the current preset from the list
    const availablePresets = presetsQuery.data?.filter((p) => p.id !== presetId) || [];

    const handleOk = async () => {
        try {
            const values = await form.validateFields();
            replacePreset(
                {
                    url: `/api/v1/filament-preset/${presetId}/replace`,
                    method: "post",
                    values: {
                        new_preset_id: values.new_preset_id,
                    },
                    successNotification: {
                        message: t("notifications.replaceSuccess", "Preset replaced and deleted successfully."),
                        type: "success",
                    },
                    errorNotification: {
                        message: t("notifications.replaceError", "Failed to replace preset."),
                        type: "error",
                    },
                },
                {
                    onSuccess: () => {
                        form.resetFields();
                        onClose();
                        invalidate({ resource: "filament-preset", invalidates: ["list"] });
                        if (onSuccess) onSuccess();
                    },
                }
            );
        } catch (error) {
            console.error("Validation failed:", error);
        }
    };

    return (
        <Modal
            title={t("filament.preset.replace_title", "Replace Filament Preset")}
            open={isOpen}
            onOk={handleOk}
            onCancel={onClose}
            confirmLoading={isSubmitting}
        >
            <p>
                {t(
                    "filament.preset.replace_description",
                    "This preset is in use. Please select a new preset to replace it with before deletion."
                )}
            </p>
            <Form form={form} layout="vertical">
                <Form.Item
                    name="new_preset_id"
                    label={t("filament.fields.preset", "New Preset")}
                    rules={[{ required: true, message: t("required_field", "This field is required") }]}
                >
                    <Select
                        loading={presetsQuery.isLoading}
                        options={availablePresets.map((p) => ({ label: p.name, value: p.id }))}
                        placeholder={t("filament.form.select_preset", "Select a preset")}
                    />
                </Form.Item>
            </Form>
        </Modal>
    );
};
