const SAMPLE_MODEL_BASE =
  "https://raw.githubusercontent.com/google/model-viewer/master/packages/shared-assets/models/";

export type SampleModelUrl = {
  title: string;
  value: string;
};

const SAMPLE_GLB_FILES: Array<{ title: string; file: string }> = [
  { title: "Astronaut (Google Model Viewer Repo)", file: "Astronaut.glb" },
  { title: "Astronaut (Unlit) (Google Model Viewer Repo)", file: "Astronaut-Unlit.glb" },
  { title: "Astronaut (DRACO) (Google Model Viewer Repo)", file: "AstronautDRACO.glb" },
  { title: "Barramundi Fish (Google Model Viewer Repo)", file: "BarramundiFish.mixed.glb" },
  { title: "Duplicate Animation Names (Google Model Viewer Repo)", file: "DuplicateAnimationNames.glb" },
  { title: "Emissive Strength Test (Google Model Viewer Repo)", file: "EmissiveStrengthTest.glb" },
  { title: "Horse (Google Model Viewer Repo)", file: "Horse.glb" },
  { title: "Macbeth Balls (Google Model Viewer Repo)", file: "MacbethBalls.glb" },
  { title: "Mesh Primitives Variants (Google Model Viewer Repo)", file: "MeshPrimitivesVariants.glb" },
  { title: "Neil Armstrong (Google Model Viewer Repo)", file: "NeilArmstrong.glb" },
  { title: "Robot Expressive", file: "RobotExpressive.glb" },
  { title: "Rocket Ship (Google Model Viewer Repo)", file: "RocketShip.glb" },
  { title: "Alpha Blend Litmus (Google Model Viewer Repo)", file: "alpha-blend-litmus.glb" },
  { title: "Coffeemat (Google Model Viewer Repo)", file: "coffeemat.glb" },
  { title: "Manifold (Google Model Viewer Repo)", file: "manifold.glb" },
  { title: "Odd Shape (Google Model Viewer Repo)", file: "odd-shape.glb" },
  { title: "Odd Shape (Labeled) (Google Model Viewer Repo)", file: "odd-shape-labeled.glb" },
  { title: "PBR Spheres (Google Model Viewer Repo)", file: "pbr-spheres.glb" },
  { title: "Radiance (Google Model Viewer Repo)", file: "radiance.glb" },
  { title: "Shishkebab", file: "shishkebab.glb" },
  { title: "Soldier (Google Model Viewer Repo)", file: "soldier.glb" },
  { title: "Sphere (Google Model Viewer Repo)", file: "sphere.glb" },
];

export const sampleModelUrls: SampleModelUrl[] = SAMPLE_GLB_FILES.map(({ title, file }) => ({
  title,
  value: SAMPLE_MODEL_BASE + file,
}));
