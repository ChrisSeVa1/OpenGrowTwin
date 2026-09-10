"""OpenUSD interchange for OpenGrowTwin scenes and results.

Keep this package initializer dependency-free. NVIDIA Kit supplies ``pxr`` but
does not necessarily include the CPU visualization stack (notably
Matplotlib), so importing a lightweight stage reader must not load the
heatmap authoring module.
"""

__all__ = ["write_heatmap_usda"]


def __getattr__(name):
    """Preserve the public heatmap helper without importing it eagerly."""
    if name == "write_heatmap_usda":
        from .heatmap import write_heatmap_usda

        return write_heatmap_usda
    raise AttributeError(name)
