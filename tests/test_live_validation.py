import unittest
from unittest.mock import MagicMock, ANY
import tkinter as tk
from ui.logic import UILogic

class TestLiveValidation(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        
        self.mock_view = MagicMock()
        self.mock_view.automation_vars = {
            "full_auto": tk.BooleanVar(value=True),
            "enabled": tk.BooleanVar(value=False)
        }
        self.mock_view.chunk_size_var = tk.IntVar(value=50)
        self.mock_view.chunk_combo.current.return_value = 0
        
        # Initialize UILogic first
        self.logic = UILogic(self.mock_view, self.root)
        self.logic.validate_live = MagicMock()
        
        # Now mock root.after and root.after_cancel for our specific test
        self.root.after = MagicMock(return_value="mock_timer_id")
        self.root.after_cancel = MagicMock()

    def tearDown(self):
        self.root.destroy()

    def test_on_text_edited_debounce(self):
        """Test that typing rapidly cancels the old timer and sets a new one."""
        # First key press
        self.logic.on_text_edited(None)
        self.root.after.assert_called_once_with(500, ANY)
        self.root.after_cancel.assert_not_called()
        self.assertEqual(self.logic._validation_timer, "mock_timer_id")
        
        # Reset mocks
        self.root.after.reset_mock()
        self.root.after_cancel.reset_mock()
        
        # Second key press (simulating rapid typing)
        self.logic.on_text_edited(None)
        self.root.after_cancel.assert_called_once_with("mock_timer_id")
        self.root.after.assert_called_once_with(500, ANY)

    def test_auto_advance_triggered(self):
        """Test that auto-advance triggers when validation passes and full_auto is True."""
        self.logic.trigger_manual_automation = MagicMock()
        self.mock_view.lbl_status.cget.return_value = "Validation PASSED"
        self.mock_view.automation_vars["full_auto"].set(True)
        
        # Trigger edit to capture the callback
        self.logic.on_text_edited(None)
        
        # Extract the scheduled callback
        args, kwargs = self.root.after.call_args
        callback = args[1]
        
        # Execute the callback
        callback()
        
        # Verify
        self.logic.validate_live.assert_called_once()
        self.logic.trigger_manual_automation.assert_called_once()

    def test_auto_advance_skipped_when_failed(self):
        """Test that auto-advance is skipped if validation fails."""
        self.logic.trigger_manual_automation = MagicMock()
        self.mock_view.lbl_status.cget.return_value = "Validation FAILED"
        self.mock_view.automation_vars["full_auto"].set(True)
        
        self.logic.on_text_edited(None)
        
        args, kwargs = self.root.after.call_args
        callback = args[1]
        callback()
        
        self.logic.validate_live.assert_called_once()
        self.logic.trigger_manual_automation.assert_not_called()

    def test_auto_advance_skipped_when_not_full_auto(self):
        """Test that auto-advance is skipped if full_auto is False, even if validation passes."""
        self.logic.trigger_manual_automation = MagicMock()
        self.mock_view.lbl_status.cget.return_value = "Validation PASSED"
        self.mock_view.automation_vars["full_auto"].set(False)
        
        self.logic.on_text_edited(None)
        
        args, kwargs = self.root.after.call_args
        callback = args[1]
        callback()
        
        self.logic.validate_live.assert_called_once()
        self.logic.trigger_manual_automation.assert_not_called()

if __name__ == '__main__':
    unittest.main()
