import os


class PEngineUtils:

    projectDir: str = None

    def setup(projectDir: str):
        PEngineUtils.projectDir = projectDir

    def subprojectResPath(subProjectName: str):
        return os.path.join(
            PEngineUtils.projectDir, "subprojects", subProjectName, "src", "resources"
        )

    def subprojectPyPath(subProjectName: str):
        return os.path.join(
            PEngineUtils.projectDir,
            "subprojects",
            subProjectName,
            "src",
            "python",
            subProjectName,
        )
