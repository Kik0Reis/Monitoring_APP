import DataTable from "../common/DataTable";
import RowActions from "./RowActions";

// table of the records that belong to the record of the page, for example the devices of a location
// it has approve, edit and delete on each row, resource is what useCrudResource returned
function ChildrenTable({ resource, columns, loadingMessage, emptyMessage, onRowClick }) {
  return (
    <>
      {resource.error && <div className="error-message">{resource.error}</div>}

      <DataTable
        columns={columns}
        rows={resource.items}
        loading={resource.loading}
        loadingMessage={loadingMessage}
        emptyMessage={emptyMessage}
        onRowClick={onRowClick}
        actions={(item) => <RowActions item={item} resource={resource} withView={false} />}
      />
    </>
  );
}

export default ChildrenTable;
