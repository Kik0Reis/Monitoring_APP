import { Link } from "react-router-dom";

// the trail home / country / customer / location / device / camera, every part is a link except the last
// trail comes straight from the breadcrumb field of the api, trailingLabel adds a final text that is not a link
function Breadcrumbs({ trail, trailingLabel }) {
  if (!trail || trail.length === 0) {
    return null;
  }

  return (
    <nav className="breadcrumbs" aria-label="Breadcrumb">
      <Link to="/dashboard" className="breadcrumb-crumb">
        Home
      </Link>

      {trail.map((crumb, index) => {
        const isLast = index === trail.length - 1 && !trailingLabel;

        return (
          <span className="breadcrumb-item" key={`${crumb.type}-${crumb.id}`}>
            <span className="breadcrumb-separator">/</span>

            {isLast ? (
              <span className="breadcrumb-crumb breadcrumb-current">{crumb.name}</span>
            ) : (
              <Link to={crumb.path} className="breadcrumb-crumb">
                {crumb.name}
              </Link>
            )}
          </span>
        );
      })}

      {trailingLabel && (
        <span className="breadcrumb-item">
          <span className="breadcrumb-separator">/</span>
          <span className="breadcrumb-crumb breadcrumb-current">{trailingLabel}</span>
        </span>
      )}
    </nav>
  );
}

export default Breadcrumbs;
