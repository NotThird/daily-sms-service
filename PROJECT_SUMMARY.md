# Particle Simulation Game - Unity DOTS

## Project Overview
A high-performance 3D particle simulation game built with Unity DOTS (Data-Oriented Technology Stack). The simulation handles millions of particles efficiently using hierarchical data structures and allows seamless zooming from individual particles to solar system scale.

## Architecture

### Core Systems
1. Particle System
   - Handles basic particle behavior and properties
   - Uses ECS for optimal performance
   - Located in: `/Features/ParticleSystem`

2. Spatial Hierarchy
   - Manages multi-scale spatial organization
   - Octree-based particle clustering
   - Located in: `/Features/SpatialHierarchy`

3. Camera System
   - Handles seamless zooming across scales
   - Dynamic LOD management
   - Located in: `/Features/CameraSystem`

4. Physics System
   - Particle interactions and forces
   - Uses Unity Physics for DOTS
   - Located in: `/Features/PhysicsSystem`

5. Rendering System
   - Efficient particle rendering
   - LOD-based instancing
   - Located in: `/Features/RenderSystem`

### Data Flow
1. Physics System updates particle positions and velocities
2. Spatial Hierarchy organizes particles for efficient querying
3. Camera System determines visible regions and LOD levels
4. Rendering System draws visible particles at appropriate detail levels

## Implementation Status
- [ ] Initial project setup
- [ ] Basic ECS structure
- [ ] Particle component definition
- [ ] Physics system implementation
- [ ] Spatial hierarchy system
- [ ] Camera controls
- [ ] Rendering optimization
- [ ] Multi-scale visualization

## Dependencies
See `dependencies.json` for detailed dependency tracking.

## File Structure
See `file_registry.json` for complete file listing and organization.

## Getting Started
1. Clone repository
2. Open in Unity 2022.3 or later
3. Install required packages (see dependencies.json)
4. Open main scene in Features/Scenes
5. Press Play to run simulation

## Development Guidelines
- Follow ECS patterns strictly
- Keep systems focused and under 300 lines
- Update documentation with all changes
- Add tests for all new features
- Maintain YAML front matter in code files
