import CollapsibleSection from "../../../components/common/CollapsibleSection";
import DetailRow from "../../../components/common/DetailRow";
import StatusBadge from "../../../components/common/StatusBadge";
import { formatTimestamp } from "../../../utils/formatTimestamp";

// returns true when a value was sent, 0 and false count as sent
const hasValue = (value) => value !== null && value !== undefined;

// the license of the camera (from the info/licenses message), nothing when the camera has none
function LicenseSection({ license }) {
  if (!license || Object.keys(license).length === 0) {
    return null;
  }

  return (
    <CollapsibleSection title="License">
      <div className="component-detail-list">
        <DetailRow label="Licensed" bare>
          <StatusBadge
            status={license.licensed ? "online" : "critical"}
            label={license.licensed ? "Licensed" : "Not Licensed"}
          />
        </DetailRow>

        {license.begin_date && <DetailRow label="Begin Date">{license.begin_date}</DetailRow>}
        {license.end_date && <DetailRow label="End Date">{license.end_date}</DetailRow>}
        {hasValue(license.days_left) && <DetailRow label="Days Left">{license.days_left}</DetailRow>}

        {hasValue(license.last_validation_ok) && (
          <DetailRow label="Last Validation" bare>
            <StatusBadge
              status={license.last_validation_ok ? "online" : "warning"}
              label={license.last_validation_ok ? "Validated" : "Failed"}
            />
          </DetailRow>
        )}

        {license.last_validation_error && (
          <DetailRow label="Validation Error">{license.last_validation_error}</DetailRow>
        )}
        {license.last_validation_at && (
          <DetailRow label="Last Validated At">{formatTimestamp(license.last_validation_at)}</DetailRow>
        )}
      </div>
    </CollapsibleSection>
  );
}

export default LicenseSection;
