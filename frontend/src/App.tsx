import { Navigate, Route, Routes, useParams } from "react-router";
import { StudioWorkspace } from "./components/studio/studio-workspace";
import { ProjectLibrary } from "./components/studio/project-library";
import { AccountGate } from "./components/auth/account-gate";
import { SettingsPage } from "./components/settings-page";
import { NewProjectPlanForm } from "./components/series/new-project-plan-form";
import { ProjectOverview } from "./components/series/project-overview";
import { AnthologyPreviewPage } from "./components/series/anthology-preview-page";
import { ReaderPage } from "./components/series/reader-page";
import { LayoutPage } from "./components/series/layout-page";

export default function App() {
  return (
    <AccountGate>
      <Routes>
        <Route path="/login" element={<Navigate to="/projects" replace />} />
        <Route path="/" element={<ProjectLibrary />} />
        <Route path="/projects" element={<ProjectLibrary />} />
        <Route path="/projects/new" element={<NewProjectPlanForm />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="/projects/:projectId/studio" element={<StudioRoute />} />
        <Route path="/projects/:projectId/read/:episodeId" element={<ReaderPage />} />
        <Route path="/projects/:projectId/layout/:episodeId" element={<LayoutPage />} />
        <Route path="/projects/:projectId/anthology-preview" element={<AnthologyPreviewPage />} />
        <Route path="/projects/:projectId" element={<ProjectOverview />} />
        <Route path="*" element={<ProjectLibrary />} />
      </Routes>
    </AccountGate>
  );
}

function StudioRoute() {
  const { projectId } = useParams();
  return projectId ? <StudioWorkspace projectId={projectId} /> : <ProjectLibrary />;
}
