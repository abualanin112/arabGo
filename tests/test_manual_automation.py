import unittest
from unittest.mock import MagicMock, patch
import tkinter as tk
from ui.logic import UILogic

class TestManualAutomation(unittest.TestCase):
    def setUp(self):
        # Create a hidden Root for Tkinter variables to attach to
        self.root = tk.Tk()
        self.root.withdraw() # Hide it
        
        # Mock UI View
        self.mock_view = MagicMock()
        
        # Mock Tkinter variables (Now safe because root exists)
        self.mock_view.automation_vars = {
            "full_auto": tk.BooleanVar(value=True), # Enable feature
            "enabled": tk.BooleanVar(value=False)
        }
        self.mock_view.chunk_size_var = tk.IntVar(value=50)
        self.mock_view.lbl_status.cget.return_value = "PASSED" # Mock valid status
        self.mock_view.file_listbox.size.return_value = 5
        self.mock_view.file_listbox.curselection.return_value = (0,) # First file selected
        
        # FIX: Ensure chunk_combo.current() returns an integer, not a Mock
        self.mock_view.chunk_combo.current.return_value = 0
        self.logic = UILogic(self.mock_view, self.root)
        
        # Mock Session
        self.logic.session = MagicMock()
        self.logic.session.all_chunks_completed.return_value = True # Simulate full file
        
        # Mock internal methods to avoid side effects
        self.logic.validate_live = MagicMock()
        self.logic.on_save_chunk_clicked = MagicMock()
        self.logic.on_final_save_clicked = MagicMock()
        self.logic.on_file_selected = MagicMock()
        self.logic.on_chunk_selected = MagicMock()
        
    def tearDown(self):
        self.root.destroy()

    def test_automation_trigger_success(self):
        """Test full successful flow: Valid -> Save -> Finalize -> Next File"""
        self.logic.trigger_manual_automation()
        
        # 1. Validation called
        self.logic.validate_live.assert_called_once()
        
        # 2. Save called (because status was PASSED)
        self.logic.on_save_chunk_clicked.assert_called_once()
        
        # 3. Finalize called (because all chunks completed)
        self.logic.on_final_save_clicked.assert_called_once()
        
        # 4. Next file loaded (Index 1 selected)
        self.mock_view.file_listbox.selection_set.assert_called_with(1)
        self.logic.on_file_selected.assert_called()

    def test_automation_disabled(self):
        """Test logic does nothing if feature is disabled"""
        self.mock_view.automation_vars["full_auto"].set(False)
        
        self.logic.trigger_manual_automation()
        
        self.logic.validate_live.assert_not_called()
        self.logic.on_save_chunk_clicked.assert_not_called()

    def test_automation_validation_failed(self):
        """Test logic stops if validation fails"""
        self.mock_view.lbl_status.cget.return_value = "FAILED"
        
        self.logic.trigger_manual_automation()
        
        self.logic.validate_live.assert_called_once()
        self.logic.on_save_chunk_clicked.assert_not_called() # Should NOT save

    def test_automation_partial_file_smart_nav(self):
        """Test logic saves and AUTO-NAVIGATES to next pending chunk if file incomplete"""
        self.logic.session.all_chunks_completed.return_value = False
        
        # Mock a pending chunk
        mock_chunk = MagicMock()
        mock_chunk.chunk_id = 2 # Next chunk is 2
        self.logic.session.get_next_pending_chunk.return_value = mock_chunk
        
        self.logic.trigger_manual_automation()
        
        # 1. Save called
        self.logic.on_save_chunk_clicked.assert_called_once()
        
        # 2. Finalize NOT called
        self.logic.on_final_save_clicked.assert_not_called()
        
        # 3. Smart Navigation triggered
        # Expect jump to index 1 (chunk_id 2 - 1)
        # We use assert_any_call because on_chunk_selected calls current() (getter) afterwards
        self.mock_view.chunk_combo.current.assert_any_call(1)
        self.logic.on_chunk_selected.assert_called()

if __name__ == '__main__':
    unittest.main()
