from PyQt6 import QtWidgets, QtGui
import logging
import asyncio
import ResearchGuidePackage.FrontendModule.import_graph
import ResearchGuidePackage.FrontendModule.export_graph
import ResearchGuidePackage.FrontendModule.file_handler
from ResearchGuidePackage.FrontendModule import tools

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def create_menu_bar(main_window):
    """Create the menu bar for the main window."""
    menu_bar = QtWidgets.QMenuBar(main_window)
    logging.info("Creating menu bar...")

    # File menu
    file_menu = menu_bar.addMenu("&Labs")

    # New Graph action
    new_action = QtGui.QAction("&New Lab", main_window)
    new_action.setStatusTip("Create a new Laboratory")
    new_action.triggered.connect(lambda: handle_new_graph(main_window))
    file_menu.addAction(new_action)

    # Open action
    open_action = QtGui.QAction("&Open Lab", main_window)
    open_action.setShortcut("Ctrl+O")
    open_action.setStatusTip("Open Laboratory from file")
    open_action.triggered.connect(lambda: ResearchGuidePackage.FrontendModule.file_handler.open_file_dialog(main_window))
    file_menu.addAction(open_action)

    # Save action
    save_action = QtGui.QAction("&Save Lab", main_window)
    save_action.setShortcut("Ctrl+S")
    save_action.setStatusTip("Save Laboratory to file")
    save_action.triggered.connect(lambda: ResearchGuidePackage.FrontendModule.file_handler.save_file_dialog(main_window))
    file_menu.addAction(save_action)

    # Save As action
    save_as_action = QtGui.QAction("Save &As...", main_window)
    save_as_action.setStatusTip("Save Laboratory to a new file")
    save_as_action.triggered.connect(lambda: ResearchGuidePackage.FrontendModule.file_handler.save_as_file_dialog(main_window))
    file_menu.addAction(save_as_action)

    # Save Plot as Image action
    save_plot_action = QtGui.QAction("Save Plot as Image", main_window)
    save_plot_action.setStatusTip("Save the graph plot as an image")
    save_plot_action.triggered.connect(main_window.save_plot_as_image)
    file_menu.addAction(save_plot_action)

    # Add a separator
    file_menu.addSeparator()

    # Lab Metadata action
    lab_metadata_action = QtGui.QAction("Lab &Metadata", main_window)
    lab_metadata_action.setStatusTip("Show information about the Laboratory")
    lab_metadata_action.triggered.connect(lambda: handle_lab_metadata(main_window))
    file_menu.addAction(lab_metadata_action)

    # Import action
    import_action = QtGui.QAction("&Import Lab", main_window)
    import_action.setStatusTip("Import Laboratory from file")
    import_action.triggered.connect(lambda: ResearchGuidePackage.FrontendModule.import_graph.import_file(main_window))
    file_menu.addAction(import_action)

    # Export action
    export_action = QtGui.QAction("&Export Lab", main_window)
    export_action.setStatusTip("Export Laboratory to file")
    export_action.triggered.connect(lambda: ResearchGuidePackage.FrontendModule.export_graph.export_file(main_window))
    file_menu.addAction(export_action)

    # Add a separator
    file_menu.addSeparator()

    # Exit action
    exit_action = QtGui.QAction("E&xit", main_window)
    exit_action.setShortcut("Ctrl+Q")
    exit_action.setStatusTip("Exit application")
    exit_action.triggered.connect(main_window.close)
    file_menu.addAction(exit_action)

    # Tools menu
    tools_menu = menu_bar.addMenu("&Tools")

    # Console action
    console_action = QtGui.QAction("Console", main_window)
    console_action.setStatusTip("Show the backend console")
    tools_menu.addAction(console_action)

    # Create Tools instance
    tools_instance = tools.Tools(main_window)
    console_action.triggered.connect(lambda: tools_instance.show_console())

    # Help menu
    help_menu = menu_bar.addMenu("&Help")

    # About action
    about_action = QtGui.QAction("&About", main_window)
    about_action.setStatusTip("Show information about the application")
    about_action.triggered.connect(lambda: handle_about(main_window))
    help_menu.addAction(about_action)

    main_window.setMenuBar(menu_bar)
    logging.info("Menu bar created.")

def handle_new_graph(main_window):
    """Handle new graph action using the ticket system."""
    logging.info("New Graph action triggered.")
    try:
        # Create an async task to handle the operation
        asyncio.create_task(main_window.create_new_graph())
    except Exception as e:
        logging.error(f"Error in New Graph action: {e}")
        QtWidgets.QMessageBox.critical(main_window, "Error", f"Error creating new graph: {e}")

def handle_about(main_window):
    """Handle about action."""
    QtWidgets.QMessageBox.about(main_window, "About ResearchGuideUnearth", "ResearchGuideUnearth\nVersion 1.1\n\nA tool for continuous and soon automatic research.\nby Jason A. Schurawel")

def handle_lab_metadata(main_window):
    """Handle lab metadata action."""
    asyncio.create_task(show_lab_metadata(main_window))

async def show_lab_metadata(main_window):
    """Display lab metadata using ticket system."""
    graph = await main_window.get_graph()
    
    if graph:
        num_nodes = len(graph.nodes)
        num_edges = len(graph.edges)
        
        # Get modified status using ticket system
        success, content, error = await main_window.communication.request_and_get_response(
            operation="get_graph_modified_status",
            params={},
            sender="Frontend"
        )
        
        if success:
            is_modified = content.get("result", False)
        else:
            is_modified = "Unknown"
            logging.error(f"Error getting graph modified status: {error}")
        
        # Get file path using ticket system
        file_path = await main_window.get_last_saved_file_path() or "Not saved"

        message = f"Number of Nodes: {num_nodes}\n"
        message += f"Number of Edges: {num_edges}\n"
        message += f"Modified: {is_modified}\n"
        message += f"File Path: {file_path}"

        QtWidgets.QMessageBox.information(main_window, "Lab Metadata", message)
    else:
        QtWidgets.QMessageBox.information(main_window, "Lab Metadata", "No graph available")
