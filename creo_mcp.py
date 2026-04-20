#!/usr/bin/env python3
"""
CREO MCP Server - Extended Version
Model Context Protocol server for PTC Creo Parametric automation
Extended with Drawing, Layer, and Export capabilities
"""

import sys
import os
from typing import Optional, Dict, Any, List
from pathlib import Path

# Add logging to stderr for MCP debugging
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

logger.info("Starting CREO MCP Server (Extended)...")
logger.info(f"Python: {sys.version}")
logger.info(f"Executable: {sys.executable}")

try:
    from mcp.server.fastmcp import FastMCP
    logger.info("✓ FastMCP imported successfully")
except ImportError as e:
    logger.error(f"✗ Failed to import FastMCP: {e}")
    logger.error(f"Python path: {sys.path}")
    sys.exit(1)

try:
    import creopyson
    from pydantic import BaseModel, Field, field_validator
    logger.info("✓ All dependencies imported")
except ImportError as e:
    logger.error(f"✗ Failed to import dependencies: {e}")
    sys.exit(1)

# Initialize MCP server
mcp = FastMCP("Creo MCP Server Extended")

# Global CREOSON connection
_creoson_client: Optional[creopyson.Client] = None

def get_creoson_client() -> creopyson.Client:
    """Get or create CREOSON client singleton"""
    global _creoson_client
    if _creoson_client is None:
        host = os.getenv("CREOSON_HOST", "localhost")
        port = int(os.getenv("CREOSON_PORT", "9056"))
        _creoson_client = creopyson.Client(ip_adress=host, port=port)
        logger.info(f"Created CREOSON client: {host}:{port}")
    return _creoson_client

# ============================================================================
# CONNECTION & STATUS TOOLS
# ============================================================================

@mcp.tool()
def creo_connect(host: str = "localhost", port: int = 9056) -> Dict[str, Any]:
    """
    Connect to CREOSON server and Creo Parametric
    
    Args:
        host: CREOSON server host (default: localhost)
        port: CREOSON server port (default: 9056)
    
    Returns:
        Connection status and session info
    """
    try:
        client = creopyson.Client(ip_adress=host, port=port)
        client.connect()
        
        global _creoson_client
        _creoson_client = client
        
        # Get Creo info
        pwd = client.creo_pwd()
        
        return {
            "success": True,
            "message": f"Connected to CREOSON at {host}:{port}",
            "creo_working_directory": pwd
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to connect. Is CREOSON running? Start CreosonSetup.exe first."
        }

@mcp.tool()
def creo_get_status() -> Dict[str, Any]:
    """Get current Creo connection status and active file"""
    try:
        client = get_creoson_client()
        if not client.is_creo_running():
            return {"success": False, "message": "Creo is not running"}
        
        pwd = client.creo_pwd()
        
        try:
            active_file = client.file_get_active()
            file_info = {
                "file": active_file.get("file"),
                "type": active_file.get("type")
            }
        except Exception as e:
            logger.warning(f"Could not get active file: {e}")
            file_info = None
        
        return {
            "success": True,
            "creo_running": True,
            "working_directory": pwd,
            "active_file": file_info
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

# ============================================================================
# FILE MANAGEMENT TOOLS
# ============================================================================

@mcp.tool()
def creo_open_file(filename: str, dirname: Optional[str] = None, display: bool = True) -> Dict[str, Any]:
    """
    Open a file in Creo Parametric
    
    Args:
        filename: File name with extension (e.g., 'part.prt', 'assembly.asm', 'drawing.drw')
        dirname: Optional directory path
        display: Display file after opening (default: True)
    
    Returns:
        Operation result
    """
    try:
        import re
        client = get_creoson_client()
        
        # FIXED: Handle versioned files (.prt.6, .drw.1, etc.)
        # Remove numeric extensions like .1, .2, .6
        clean_filename = re.sub(r'\.\d+$', '', filename)
        
        # Log if filename was modified
        if clean_filename != filename:
            logger.info(f"Version file detected: {filename} -> {clean_filename}")
        
        client.file_open(file_=clean_filename, dirname=dirname, display=display)
        
        return {
            "success": True,
            "message": f"Opened file: {clean_filename}",
            "filename": clean_filename,
            "original_filename": filename if clean_filename != filename else None,
            "dirname": dirname
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to open {filename}"
        }

@mcp.tool()
def creo_list_files(dirname: Optional[str] = None) -> Dict[str, Any]:
    """
    List Creo files in directory
    
    Args:
        dirname: Directory to list (default: current working directory)
    
    Returns:
        List of files
    """
    try:
        client = get_creoson_client()
        
        if dirname is None:
            dirname = client.creo_pwd()
        
        files = client.file_list(file_="*", dirname=dirname)
        
        return {
            "success": True,
            "directory": dirname,
            "files": files if files else []
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

# ============================================================================
# DRAWING CREATION & MANAGEMENT TOOLS
# ============================================================================

@mcp.tool()
def creo_create_drawing(
    template: str,
    model: Optional[str] = None,
    drawing: Optional[str] = None,
    scale: Optional[float] = None,
    display: bool = True,
    activate: bool = True
) -> Dict[str, Any]:
    """
    Create a new drawing from a template
    
    Args:
        template: Template file name (e.g., 'a2_template.drw')
        model: Model name to add to drawing (default: current active model)
        drawing: New drawing name (default: derived from model name)
        scale: Drawing scale (default: 1.0)
        display: Display the drawing after creation (default: True)
        activate: Activate the drawing window after creation (default: True)
    
    Returns:
        Operation result with drawing name
    """
    try:
        client = get_creoson_client()
        result = client.drawing_create(
            template=template,
            model=model,
            drawing=drawing,
            scale=scale,
            display=display,
            activate=activate
        )
        
        return {
            "success": True,
            "message": f"Created drawing from template: {template}",
            "template": template,
            "drawing": drawing or "auto-generated",
            "model": model,
            "result": result
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to create drawing from template {template}"
        }

@mcp.tool()
def creo_add_model_to_drawing(model: str, drawing: Optional[str] = None) -> Dict[str, Any]:
    """
    Add a model to a drawing
    
    Args:
        model: Model name to add
        drawing: Drawing name (default: current active drawing)
    
    Returns:
        Operation result
    """
    try:
        client = get_creoson_client()
        client.drawing_add_model(model=model, drawing=drawing)
        
        return {
            "success": True,
            "message": f"Added model {model} to drawing",
            "model": model,
            "drawing": drawing or "active"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@mcp.tool()
def creo_add_sheet(position: Optional[int] = None, drawing: Optional[str] = None) -> Dict[str, Any]:
    """
    Add a sheet to a drawing
    
    Args:
        position: Position to insert sheet (default: end of drawing)
        drawing: Drawing name (default: current active drawing)
    
    Returns:
        Operation result
    """
    try:
        client = get_creoson_client()
        client.drawing_add_sheet(position=position, drawing=drawing)
        
        return {
            "success": True,
            "message": f"Added sheet to drawing",
            "position": position or "end",
            "drawing": drawing or "active"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

# ============================================================================
# VIEW MANAGEMENT TOOLS
# ============================================================================

@mcp.tool()
def creo_create_general_view(
    model_view: str,
    point: Dict[str, float],
    drawing: Optional[str] = None,
    view_name: Optional[str] = None,
    sheet: Optional[int] = None,
    model: Optional[str] = None,
    scale: Optional[float] = None
) -> Dict[str, Any]:
    """
    Create a general view on a drawing
    
    Args:
        model_view: Model view name for orientation (e.g., 'FRONT', 'TOP', 'RIGHT')
        point: Coordinates for view placement {"x": 100, "y": 150} in drawing units
        drawing: Drawing name (default: current active drawing)
        view_name: Name for new view (default: uses model_view name)
        sheet: Sheet number (default: current active sheet)
        model: Model to show in view (default: current active model)
        scale: View scale (default: sheet scale)
    
    Returns:
        Operation result
    """
    try:
        client = get_creoson_client()
        client.drawing_create_gen_view(
            model_view=model_view,
            point=point,
            drawing=drawing,
            view=view_name,
            sheet=sheet,
            model=model,
            scale=scale
        )
        
        return {
            "success": True,
            "message": f"Created general view: {view_name or model_view}",
            "model_view": model_view,
            "view_name": view_name or model_view,
            "position": point,
            "sheet": sheet or "active"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to create view {view_name or model_view}"
        }

@mcp.tool()
def creo_create_projection_view(
    parent_view: str,
    point: Dict[str, float],
    drawing: Optional[str] = None,
    view_name: Optional[str] = None,
    sheet: Optional[int] = None
) -> Dict[str, Any]:
    """
    Create a projection view from a parent view
    
    Args:
        parent_view: Parent view name to project from
        point: Offset coordinates {"x": 0, "y": -100} relative to parent view
        drawing: Drawing name (default: current active drawing)
        view_name: Name for new view (default: auto-generated)
        sheet: Sheet number (default: current active sheet)
    
    Returns:
        Operation result
    """
    try:
        client = get_creoson_client()
        client.drawing_create_proj_view(
            parent_view=parent_view,
            point=point,
            drawing=drawing,
            view=view_name,
            sheet=sheet
        )
        
        return {
            "success": True,
            "message": f"Created projection view from {parent_view}",
            "parent_view": parent_view,
            "view_name": view_name or "auto-generated",
            "offset": point
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@mcp.tool()
def creo_list_views(drawing: Optional[str] = None) -> Dict[str, Any]:
    """
    List all views in a drawing
    
    Args:
        drawing: Drawing name (default: current active drawing)
    
    Returns:
        List of views with their properties
    """
    try:
        client = get_creoson_client()
        views = client.drawing_list_views(drawing=drawing)
        
        return {
            "success": True,
            "drawing": drawing or "active",
            "views": views if views else [],
            "count": len(views) if views else 0
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@mcp.tool()
def creo_delete_view(
    view_name: str,
    drawing: Optional[str] = None,
    sheet: Optional[int] = None,
    delete_children: bool = False
) -> Dict[str, Any]:
    """
    Delete a view from a drawing
    
    Args:
        view_name: Name of view to delete
        drawing: Drawing name (default: current active drawing)
        sheet: Sheet number (optional: only delete if on this sheet)
        delete_children: Also delete child views (default: False)
    
    Returns:
        Operation result
    """
    try:
        client = get_creoson_client()
        client.drawing_delete_view(
            view=view_name,
            drawing=drawing,
            sheet=sheet,
            del_children=delete_children
        )
        
        return {
            "success": True,
            "message": f"Deleted view: {view_name}",
            "view": view_name,
            "deleted_children": delete_children
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

# ============================================================================
# EXPORT TOOLS
# ============================================================================

@mcp.tool()
def creo_export_pdf(
    filename: str,
    height: Optional[float] = None,
    width: Optional[float] = None,
    dpi: Optional[int] = None
) -> Dict[str, Any]:
    """
    Export drawing as 3D PDF
    
    Args:
        filename: Output PDF filename (e.g., 'drawing.pdf')
        height: Page height (optional)
        width: Page width (optional)
        dpi: DPI resolution (optional)
    
    Returns:
        Export result with file path
    """
    try:
        client = get_creoson_client()
        
        # Build export options
        options = {}
        if height is not None:
            options['height'] = height
        if width is not None:
            options['width'] = width
        if dpi is not None:
            options['dpi'] = dpi
        
        result = client.interface_export_3dpdf(filename=filename, **options)
        
        return {
            "success": True,
            "message": f"Exported PDF: {filename}",
            "filename": filename,
            "result": result
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to export PDF {filename}"
        }

@mcp.tool()
def creo_export_image(
    filename: str,
    file_type: str = "JPEG",
    height: Optional[int] = None,
    width: Optional[int] = None,
    dpi: Optional[int] = None
) -> Dict[str, Any]:
    """
    Export current view as image
    
    Args:
        filename: Output filename (e.g., 'output.jpg')
        file_type: Image type - BMP, EPS, JPEG, TIFF (default: JPEG)
        height: Image height in pixels (optional)
        width: Image width in pixels (optional)
        dpi: DPI resolution (optional)
    
    Returns:
        Export result with file path
    """
    try:
        client = get_creoson_client()
        
        # FIXED: Clean parameters (remove None values)
        params = {
            "file_type": file_type,
            "filename": filename
        }
        
        if height is not None:
            params["height"] = height
        if width is not None:
            params["width"] = width
        if dpi is not None:
            params["dpi"] = dpi
        
        result = client.interface_export_image(**params)
        
        # Get working directory for full path
        pwd = client.creo_pwd()
        full_path = f"{pwd}{filename}"
        
        return {
            "success": True,
            "message": f"Exported image: {filename}",
            "filename": filename,
            "full_path": full_path,
            "file_type": file_type,
            "result": result
        }
    except Exception as e:
        error_msg = str(e)
        
        # FIXED: More informative error messages
        if "General Error" in error_msg:
            return {
                "success": False,
                "error": error_msg,
                "message": "Export failed. Note: interface_export_image works with 3D models. For drawings, some settings may not apply. Try adjusting height/width or use default settings."
            }
        
        return {
            "success": False,
            "error": error_msg,
            "message": f"Failed to export image: {filename}"
        }

@mcp.tool()
def creo_export_step(
    filename: str,
    dirname: Optional[str] = None,
    geom_flags: str = "solids"
) -> Dict[str, Any]:
    """
    Export model as STEP file
    
    Args:
        filename: Output STEP filename (e.g., 'part.stp' or 'part.step')
        dirname: Output directory (default: current working directory)
        geom_flags: Geometry type - solids, surfaces, wireframe, etc. (default: solids)
    
    Returns:
        Export result
    """
    try:
        client = get_creoson_client()
        
        result = client.interface_export_file(
            file_type="STEP",
            filename=filename,
            dirname=dirname,
            geom_flags=geom_flags
        )
        
        return {
            "success": True,
            "message": f"Exported STEP: {filename}",
            "filename": filename,
            "directory": dirname or "current",
            "result": result
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@mcp.tool()
def creo_export_iges(
    filename: str,
    dirname: Optional[str] = None,
    geom_flags: str = "solids"
) -> Dict[str, Any]:
    """
    Export model as IGES file
    
    Args:
        filename: Output IGES filename (e.g., 'part.igs' or 'part.iges')
        dirname: Output directory (default: current working directory)
        geom_flags: Geometry type - solids, surfaces, wireframe, etc. (default: solids)
    
    Returns:
        Export result
    """
    try:
        client = get_creoson_client()
        
        result = client.interface_export_file(
            file_type="IGES",
            filename=filename,
            dirname=dirname,
            geom_flags=geom_flags
        )
        
        return {
            "success": True,
            "message": f"Exported IGES: {filename}",
            "filename": filename,
            "directory": dirname or "current",
            "result": result
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

# ============================================================================
# LAYER MANAGEMENT TOOLS
# ============================================================================

@mcp.tool()
def creo_list_layers(filename: Optional[str] = None) -> Dict[str, Any]:
    """
    List all layers in a file (model or drawing)
    
    Args:
        filename: File name (default: current active file)
    
    Returns:
        List of layers with their properties
    """
    try:
        client = get_creoson_client()
        layers = client.layer_list(file_=filename)
        
        return {
            "success": True,
            "file": filename or "active",
            "layers": layers if layers else [],
            "count": len(layers) if layers else 0
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@mcp.tool()
def creo_show_layer(layer_name: str, filename: Optional[str] = None) -> Dict[str, Any]:
    """
    Show (make visible) a layer
    
    Args:
        layer_name: Layer name to show
        filename: File name (default: current active file)
    
    Returns:
        Operation result
    """
    try:
        client = get_creoson_client()
        client.layer_show(name=layer_name, file_=filename)
        
        return {
            "success": True,
            "message": f"Showed layer: {layer_name}",
            "layer": layer_name,
            "file": filename or "active"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@mcp.tool()
def creo_hide_layer(layer_name: str, filename: Optional[str] = None) -> Dict[str, Any]:
    """
    Hide (make invisible) a layer
    
    Args:
        layer_name: Layer name to hide
        filename: File name (default: current active file)
    
    Returns:
        Operation result
    """
    try:
        client = get_creoson_client()
        # FIXED: Use layer_show with show_=False to hide
        client.layer_show(name=layer_name, file_=filename, show_=False)
        
        return {
            "success": True,
            "message": f"Hid layer: {layer_name}",
            "layer": layer_name,
            "file": filename or "active"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

# ============================================================================
# QUERY & INFO TOOLS
# ============================================================================

@mcp.tool()
def creo_get_drawing_info(drawing: Optional[str] = None) -> Dict[str, Any]:
    """
    Get comprehensive information about a drawing
    
    Args:
        drawing: Drawing name (default: current active drawing)
    
    Returns:
        Drawing information including models, views, sheets, scale
    """
    try:
        client = get_creoson_client()
        
        # Get multiple pieces of info
        info = {}
        
        # Get models in drawing
        try:
            models = client.drawing_list_models(drawing=drawing)
            info['models'] = models if models else []
        except Exception as e:
            logger.warning(f"drawing_list_models failed: {e}")
            info['models'] = []
        
        # Get views
        try:
            views = client.drawing_list_views(drawing=drawing)
            info['views'] = views if views else []
            info['view_count'] = len(views) if views else 0
        except Exception as e:
            logger.warning(f"drawing_list_views failed: {e}")
            info['views'] = []
            info['view_count'] = 0
        
        # Get current model
        try:
            current_model = client.drawing_get_cur_model(drawing=drawing)
            info['current_model'] = current_model
        except Exception as e:
            logger.warning(f"drawing_get_cur_model failed: {e}")
            info['current_model'] = None
        
        # Get current sheet
        try:
            current_sheet = client.drawing_get_cur_sheet(drawing=drawing)
            info['current_sheet'] = current_sheet
        except Exception as e:
            logger.warning(f"drawing_get_cur_sheet failed: {e}")
            info['current_sheet'] = None
        
        return {
            "success": True,
            "drawing": drawing or "active",
            "info": info
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@mcp.tool()
def creo_get_model_info(model: Optional[str] = None) -> Dict[str, Any]:
    """
    Get information about a model (part or assembly)
    
    Args:
        model: Model name (default: current active model)
    
    Returns:
        Model information including type, mass properties, parameters
    """
    try:
        client = get_creoson_client()
        
        info = {}
        
        # Get active file info if no model specified
        if model is None:
            active = client.file_get_active()
            model = active.get('file')
            info['type'] = active.get('type')
        
        # Get mass properties
        try:
            mass_props = client.file_massprops(file_=model)
            info['mass_properties'] = mass_props
        except Exception as e:
            logger.warning(f"file_massprops failed: {e}")
            info['mass_properties'] = None
        
        # Get parameters
        try:
            params = client.parameter_list(file_=model)
            info['parameters'] = params if params else []
        except Exception as e:
            logger.warning(f"parameter_list failed: {e}")
            info['parameters'] = []
        
        return {
            "success": True,
            "model": model,
            "info": info
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

# ============================================================================
# COLOR & APPEARANCE TOOLS
# ============================================================================

@mcp.tool()
def creo_set_standard_color(
    color_type: str,
    red: int,
    green: int,
    blue: int
) -> Dict[str, Any]:
    """
    Set one of Creo standard UI colors (palette, not per-surface).

    Args:
        color_type: One of: letter, highlight, drawing, background, half_tone,
                    edge_highlight, dimmed, error, warning, sheetmetal, curve,
                    presel_highlight, selected, secondary_selected, preview,
                    secondary_preview, datum, quilt.
        red: Red value (0-255)
        green: Green value (0-255)
        blue: Blue value (0-255)

    Returns:
        Operation result
    """
    VALID_TYPES = {
        "letter", "highlight", "drawing", "background", "half_tone",
        "edge_highlight", "dimmed", "error", "warning", "sheetmetal",
        "curve", "presel_highlight", "selected", "secondary_selected",
        "preview", "secondary_preview", "datum", "quilt"
    }
    if color_type not in VALID_TYPES:
        return {
            "success": False,
            "error": f"Invalid color_type '{color_type}'. Valid values: {sorted(VALID_TYPES)}"
        }
    try:
        client = get_creoson_client()
        client.creo_set_std_color(color_type=color_type, red=red, green=green, blue=blue)
        return {
            "success": True,
            "message": f"Set Creo standard color '{color_type}' to RGB({red},{green},{blue})",
            "color_type": color_type,
            "color": {"red": red, "green": green, "blue": blue}
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    logger.info("Running MCP server (Extended version)...")
    mcp.run()
