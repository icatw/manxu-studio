import { Navigate, Route, Routes, useParams } from "react-router";
import { StudioWorkspace } from "./components/studio/studio-workspace";
import { ProjectLibrary } from "./components/studio/project-library";
import { AccountGate } from "./components/auth/account-gate";
import { SettingsPage } from "./components/settings-page";

export default function App() {
  return (
    <AccountGate>
      <Routes>
        <Route path="/login" element={<Navigate to="/projects" replace />} />
        <Route path="/" element={<ProjectLibrary />} />
        <Route path="/projects" element={<ProjectLibrary />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="/projects/:projectId" element={<ProjectRoute />} />
        <Route path="*" element={<ProjectLibrary />} />
      </Routes>
    </AccountGate>
  );
}

function ProjectRoute() {
  const { projectId } = useParams();
  return projectId ? <StudioWorkspace projectId={projectId} /> : <ProjectLibrary />;
}
