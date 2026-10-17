import FormField from "../common/FormField";
import CrudModal from "./CrudModal";

// the add, edit and details popup of a list page
// entity: the name shown in the title, for example "Device"
// fields: the form fields (see FormField), details(item): returns [label, value] pairs shown in view mode
// details is not needed on pages that only create and edit, onSubmit replaces the default save when the page needs more
function ResourceModal({ resource, entity, fields, details, onSubmit }) {
  if (!resource.modalMode) {
    return null;
  }

  const titles = {
    create: `Add ${entity}`,
    edit: `Edit ${entity}`,
    view: `${entity} Details`,
  };

  return (
    <CrudModal
      mode={resource.modalMode}
      title={titles[resource.modalMode]}
      onClose={resource.closeModal}
      onSubmit={onSubmit ?? resource.handleSubmit}
      loading={resource.saving}
    >
      {resource.modalMode === "view" ? (
        <div className="crud-details">
          {details?.(resource.selected ?? {}).map(([label, value]) => (
            <div className="crud-detail" key={label}>
              <span>{label}</span>
              <strong>{value}</strong>
            </div>
          ))}
        </div>
      ) : (
        <div className="crud-form">
          {fields.map((field) => (
            <FormField
              key={field.name}
              field={field}
              value={resource.formData[field.name]}
              onChange={resource.handleFormChange}
              disabled={resource.saving}
            />
          ))}
        </div>
      )}
    </CrudModal>
  );
}

export default ResourceModal;
