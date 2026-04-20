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

# ============================================================================
# CORE SESSION TOOLS — F8.1 (regen, save, list models, parameters, family table)
# ============================================================================

@mcp.tool()
def creo_regen(model: Optional[str] = None, display: bool = True) -> Dict[str, Any]:
    """
    Regenerate a model (equivalent to Ctrl+G in Creo).
    Must be called after parameter changes to propagate geometry updates.

    Args:
        model: Model name (default: active model)
        display: Refresh display after regen (default: True)
    """
    try:
        client = get_creoson_client()
        client.file_regenerate(file_=model, display=display)
        return {
            "success": True,
            "message": f"Regenerated: {model or 'active model'}",
            "model": model or "active"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
def creo_save(model: Optional[str] = None) -> Dict[str, Any]:
    """
    Save a model to disk.

    Args:
        model: Model name (default: active model)
    """
    try:
        client = get_creoson_client()
        client.file_save(file_=model)
        return {
            "success": True,
            "message": f"Saved: {model or 'active model'}",
            "model": model or "active"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
def creo_save_all() -> Dict[str, Any]:
    """Save all open models in the current Creo session."""
    try:
        client = get_creoson_client()
        files = client.file_list(file_="*") or []
        saved, failed = [], []
        for f in files:
            fname = f if isinstance(f, str) else f.get("file", "")
            if not fname:
                continue
            try:
                client.file_save(file_=fname)
                saved.append(fname)
            except Exception as e:
                failed.append({"file": fname, "error": str(e)})
        return {
            "success": True,
            "saved": saved,
            "failed": failed,
            "saved_count": len(saved),
            "failed_count": len(failed)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
def creo_list_models() -> Dict[str, Any]:
    """List all models currently open in the Creo session."""
    try:
        client = get_creoson_client()
        files = client.file_list(file_="*") or []
        _EXT_TYPE = {"prt": "PART", "asm": "ASSEMBLY", "drw": "DRAWING", "frm": "FORMAT"}
        models = []
        for f in files:
            if isinstance(f, str):
                ext = f.rsplit(".", 1)[-1].lower() if "." in f else ""
                models.append({"file": f, "type": _EXT_TYPE.get(ext, "UNKNOWN")})
            elif isinstance(f, dict):
                models.append(f)
        return {"success": True, "models": models, "count": len(models)}
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
def creo_get_parameters(
    model: Optional[str] = None,
    name_filter: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get parameters of a model.

    Args:
        model: Model name (default: active model)
        name_filter: Filter by parameter name pattern (e.g. 'MATERIAL*')
    """
    try:
        client = get_creoson_client()
        params = client.parameter_list(name=name_filter, file_=model) or []
        return {
            "success": True,
            "model": model or "active",
            "parameters": params,
            "count": len(params)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
def creo_set_parameter(
    name: str,
    value: Any,
    model: Optional[str] = None,
    param_type: str = "STRING"
) -> Dict[str, Any]:
    """
    Set a parameter value on a model. Call creo_regen after to propagate changes.

    Args:
        name: Parameter name
        value: New value
        model: Model name (default: active model)
        param_type: Value type — STRING, DOUBLE, INTEGER, BOOL, NOTE (default: STRING)
    """
    VALID_TYPES = {"STRING", "DOUBLE", "INTEGER", "BOOL", "NOTE"}
    if param_type not in VALID_TYPES:
        return {"success": False, "error": f"Invalid param_type '{param_type}'. Valid: {sorted(VALID_TYPES)}"}
    try:
        client = get_creoson_client()
        client.parameter_set(name=name, value=value, file_=model, type_=param_type)
        return {
            "success": True,
            "message": f"Set '{name}' = {value} ({param_type})",
            "name": name,
            "value": value,
            "type": param_type,
            "model": model or "active"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
def creo_get_family_table(model: Optional[str] = None) -> Dict[str, Any]:
    """
    Get the family table of a model (all instances/variants).

    Args:
        model: Model name (default: active model)
    """
    try:
        client = get_creoson_client()
        header = client.familytable_get_header(file_=model) or []
        rows = client.familytable_list_rows(file_=model) or []
        instances = []
        for row_name in rows:
            try:
                row_data = client.familytable_get_row(instance=row_name, file_=model)
                instances.append({"name": row_name, "values": row_data})
            except Exception as e:
                logger.warning(f"Could not get row '{row_name}': {e}")
                instances.append({"name": row_name, "error": str(e)})
        return {
            "success": True,
            "model": model or "active",
            "columns": header,
            "instances": instances,
            "count": len(instances)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============================================================================
# ASSEMBLY & BOM TOOLS — F8.2
# ============================================================================

@mcp.tool()
def creo_list_components(
    assembly: Optional[str] = None,
    top_level_only: bool = False
) -> Dict[str, Any]:
    """
    List components of an assembly with hierarchy.

    Args:
        assembly: Assembly file name (default: active model)
        top_level_only: Only return top-level components (default: False = recursive)
    """
    try:
        client = get_creoson_client()
        paths = client.bom_get_paths(
            file_=assembly,
            paths=True,
            skeleton=False,
            top_level=top_level_only
        )
        return {
            "success": True,
            "assembly": assembly or "active",
            "components": paths if paths else [],
            "top_level_only": top_level_only
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
def creo_get_bom(
    assembly: Optional[str] = None,
    recursive: bool = True
) -> Dict[str, Any]:
    """
    Generate a Bill of Materials (BOM) from an assembly.
    Returns a flat list with part numbers, types, and quantities.

    Args:
        assembly: Assembly file name (default: active model)
        recursive: Include sub-assemblies recursively (default: True)
    """
    try:
        client = get_creoson_client()
        paths = client.bom_get_paths(
            file_=assembly,
            paths=True,
            skeleton=False,
            top_level=not recursive
        )

        _EXT_TYPE = {"prt": "PART", "asm": "SUBASSEMBLY"}
        bom: Dict[str, Any] = {}

        def _walk(items: Any, level: int = 0) -> None:
            if not items:
                return
            if isinstance(items, dict):
                items = [items]
            for item in items:
                if not isinstance(item, dict):
                    continue
                fname = item.get("file", "")
                if fname:
                    ext = fname.rsplit(".", 1)[-1].lower() if "." in fname else ""
                    if fname in bom:
                        bom[fname]["qty"] += 1
                    else:
                        bom[fname] = {
                            "file": fname,
                            "type": _EXT_TYPE.get(ext, "PART"),
                            "qty": 1,
                            "level": level
                        }
                _walk(item.get("children"), level + 1)

        _walk(paths)
        bom_list = sorted(bom.values(), key=lambda x: (x["level"], x["file"]))
        return {
            "success": True,
            "assembly": assembly or "active",
            "bom": bom_list,
            "total_unique_items": len(bom_list),
            "total_quantity": sum(i["qty"] for i in bom_list)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
def creo_check_interference(assembly: Optional[str] = None) -> Dict[str, Any]:
    """
    Check for geometric interferences between components in an assembly.

    Args:
        assembly: Assembly file name (default: active model)
    """
    try:
        client = get_creoson_client()
        result = client.geometry_get_edges(file_=assembly)
        # geometry_get_edges is a probe — real interference uses a different CREOSON path.
        # Return informational response pointing to the correct workflow.
        return {
            "success": False,
            "message": "creo_check_interference requires CREOSON Interference Analysis which is not yet exposed in creopyson 0.7.8. Use Creo menu: Analysis → Model → Global Interference.",
            "workaround": "Run 'Analysis > Model > Global Interference' in Creo manually, or call creo_get_model_info to inspect geometry."
        }
    except Exception as e:
        return {
            "success": False,
            "message": "Interference check not available via CREOSON in this version.",
            "error": str(e)
        }


@mcp.tool()
def creo_add_component(
    component: str,
    assembly: Optional[str] = None,
    package_assembly: bool = False
) -> Dict[str, Any]:
    """
    Add a component (part or subassembly) to an assembly.
    The component is added as a packaged (unplaced) component if package_assembly=True,
    or using default placement constraints otherwise.

    Args:
        component: Component file name to add (e.g., 'bolt_m6.prt')
        assembly: Target assembly (default: active model)
        package_assembly: Add as packaged/unplaced component (default: False)
    """
    try:
        client = get_creoson_client()
        result = client.asm_add_component(
            file_=component,
            assembly=assembly,
            package_assembly=package_assembly
        )
        return {
            "success": True,
            "message": f"Added component '{component}' to assembly",
            "component": component,
            "assembly": assembly or "active",
            "result": result
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============================================================================
# ADVANCED DRAWING TOOLS — F8.3 (notes, dimensions, title block, tables)
# ============================================================================

@mcp.tool()
def creo_add_note(
    text: str,
    point: Optional[Dict[str, float]] = None,
    drawing: Optional[str] = None,
    name: Optional[str] = None,
    sheet: Optional[int] = None
) -> Dict[str, Any]:
    """
    Add a text note to a drawing.

    Args:
        text: Note text content (use \\n for line breaks)
        point: Position {"x": 100, "y": 150} in drawing units (default: center of sheet)
        drawing: Drawing name (default: active drawing)
        name: Note name/identifier (default: auto-generated)
        sheet: Sheet number (default: active sheet)
    """
    try:
        client = get_creoson_client()
        kwargs: Dict[str, Any] = {"text": [text] if isinstance(text, str) else text, "file_": drawing}
        if name:
            kwargs["name"] = name
        if point:
            kwargs["location"] = point
        if sheet:
            kwargs["sheet"] = sheet
        result = client.note_set(**kwargs)
        return {
            "success": True,
            "message": f"Added note to drawing",
            "text": text,
            "drawing": drawing or "active",
            "result": result
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
def creo_get_notes(drawing: Optional[str] = None) -> Dict[str, Any]:
    """
    List all notes in a drawing.

    Args:
        drawing: Drawing name (default: active drawing)
    """
    try:
        client = get_creoson_client()
        notes = client.note_list(file_=drawing) or []
        return {
            "success": True,
            "drawing": drawing or "active",
            "notes": notes,
            "count": len(notes)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
def creo_set_title_block(
    fields: Dict[str, str],
    drawing: Optional[str] = None
) -> Dict[str, Any]:
    """
    Set title block fields in a drawing by writing parameters with matching names.
    Creo title blocks are typically driven by drawing parameters.

    Args:
        fields: Dict of field_name → value (e.g. {"TITLE": "My Part", "DRW_NO": "001", "REVISION": "A"})
        drawing: Drawing name (default: active drawing)
    """
    try:
        client = get_creoson_client()
        set_ok, failed = [], []
        for name, value in fields.items():
            try:
                client.parameter_set(name=name, value=str(value), file_=drawing, type_="STRING")
                set_ok.append(name)
            except Exception as e:
                logger.warning(f"Could not set title block field '{name}': {e}")
                failed.append({"field": name, "error": str(e)})
        return {
            "success": len(failed) == 0,
            "message": f"Set {len(set_ok)} title block fields",
            "set": set_ok,
            "failed": failed,
            "drawing": drawing or "active"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
def creo_add_dimension(
    ref1: str,
    ref2: Optional[str] = None,
    drawing: Optional[str] = None,
    dim_type: str = "LINEAR"
) -> Dict[str, Any]:
    """
    Add a driven dimension to a drawing.
    Note: driven dimensions reference geometry; use Creo's 'Show Model Annotations'
    workflow for driven dims from model. This creates a reference dimension.

    Args:
        ref1: First geometry reference (view + entity, e.g. 'FRONT:edge_1')
        ref2: Second reference for linear dims (optional for radius/diameter)
        drawing: Drawing name (default: active drawing)
        dim_type: LINEAR, RADIAL, DIAMETER, ANGULAR (default: LINEAR)
    """
    try:
        client = get_creoson_client()
        result = client.drawing_add_draft_dim(
            drawing=drawing,
            ref1=ref1,
            ref2=ref2,
            type_=dim_type
        )
        return {
            "success": True,
            "message": f"Added {dim_type} dimension",
            "dim_type": dim_type,
            "drawing": drawing or "active",
            "result": result
        }
    except AttributeError:
        return {
            "success": False,
            "message": "drawing_add_draft_dim not available in this creopyson version. Use 'Show Model Annotations' in Creo to display model dimensions on the drawing.",
            "workaround": "Creo menu: View > Show Model Annotations > Dimensions"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
def creo_add_table(
    rows: int,
    cols: int,
    drawing: Optional[str] = None,
    point: Optional[Dict[str, float]] = None,
    sheet: Optional[int] = None
) -> Dict[str, Any]:
    """
    Create a table on a drawing (for BOM, legend, etc.).

    Args:
        rows: Number of rows
        cols: Number of columns
        drawing: Drawing name (default: active drawing)
        point: Position {"x": 10, "y": 10} in drawing units (default: auto-placed)
        sheet: Sheet number (default: active sheet)
    """
    try:
        client = get_creoson_client()
        kwargs: Dict[str, Any] = {
            "nrows": rows,
            "ncols": cols,
            "file_": drawing
        }
        if point:
            kwargs["location"] = point
        if sheet:
            kwargs["sheet"] = sheet
        result = client.drawing_create_draft_table(**kwargs)
        return {
            "success": True,
            "message": f"Created {rows}x{cols} table on drawing",
            "rows": rows,
            "cols": cols,
            "drawing": drawing or "active",
            "result": result
        }
    except AttributeError:
        return {
            "success": False,
            "message": "drawing_create_draft_table not available in this creopyson version.",
            "workaround": "Add tables manually in Creo: Table > Insert Table"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============================================================================
# ANALYSIS & MEASUREMENT TOOLS — F8.4
# ============================================================================

@mcp.tool()
def creo_get_mass_properties(model: Optional[str] = None) -> Dict[str, Any]:
    """
    Get mass properties of a model: volume, surface area, mass, center of gravity,
    inertia moments. Requires material density to be set for mass calculation.

    Args:
        model: Model name (default: active model)
    """
    try:
        client = get_creoson_client()
        props = client.file_massprops(file_=model)
        return {
            "success": True,
            "model": model or "active",
            "mass_properties": props
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
def creo_measure_distance(
    ref1: str,
    ref2: str,
    model: Optional[str] = None
) -> Dict[str, Any]:
    """
    Measure the minimum distance between two geometric entities.

    Args:
        ref1: First reference — surface/edge/point name or selection string
        ref2: Second reference
        model: Model name (default: active model)
    """
    try:
        client = get_creoson_client()
        result = client.geometry_get_distance(
            file_=model,
            ref1=ref1,
            ref2=ref2
        )
        return {
            "success": True,
            "model": model or "active",
            "ref1": ref1,
            "ref2": ref2,
            "distance": result
        }
    except AttributeError:
        return {
            "success": False,
            "message": "geometry_get_distance not available in this creopyson version.",
            "workaround": "Use Analysis > Measure > Distance in Creo."
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
def creo_measure_area(
    surface_refs: List[str],
    model: Optional[str] = None
) -> Dict[str, Any]:
    """
    Calculate the total surface area of one or more faces.

    Args:
        surface_refs: List of surface/face reference names
        model: Model name (default: active model)
    """
    try:
        client = get_creoson_client()
        total_area = 0.0
        results = []
        for ref in surface_refs:
            try:
                area = client.geometry_get_area(file_=model, surface=ref)
                total_area += float(area) if area else 0.0
                results.append({"surface": ref, "area": area})
            except Exception as e:
                results.append({"surface": ref, "error": str(e)})
        return {
            "success": True,
            "model": model or "active",
            "surfaces": results,
            "total_area": total_area
        }
    except AttributeError:
        return {
            "success": False,
            "message": "geometry_get_area not available in this creopyson version.",
            "workaround": "Use Analysis > Measure > Area in Creo."
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    logger.info("Running MCP server (Extended version)...")
    mcp.run()
