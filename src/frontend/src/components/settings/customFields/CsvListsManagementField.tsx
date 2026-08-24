import { CsvListManager } from '../../CsvListManager';
import type { CustomSettingsFieldRendererProps } from './types';

export const CsvListsManagementField = ({
  onShowToast,
  onSettingsSaved,
}: CustomSettingsFieldRendererProps) => {
  const handleChanged = () => {
    onSettingsSaved?.();
    onShowToast?.('CSV lists updated', 'success');
  };

  return <CsvListManager onChanged={handleChanged} />;
};
