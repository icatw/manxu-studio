import { Route, Routes, useParams } from "react-router";
import { StudioWorkspace } from "./components/studio/studio-workspace";
import { ProjectLibrary } from "./components/studio/project-library";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<ProjectLibrary />} />
      <Route path="/projects" element={<ProjectLibrary />} />
      <Route path="/projects/:projectId" element={<ProjectRoute />} />
      <Route path="*" element={<ProjectLibrary />} />
    </Routes>
  );
}

function ProjectRoute() {
  const { projectId } = useParams();
  return projectId ? <StudioWorkspace projectId={projectId} /> : <ProjectLibrary />;
}
