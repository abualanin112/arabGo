import unittest
from unittest.mock import MagicMock, patch
import tkinter as tk
from ui.logic import UILogic

class TestAutoCorrectionLogic(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        
        self.mock_view = MagicMock()
        self.mock_view.automation_vars = {
            "full_auto": tk.BooleanVar(value=True),
            "enabled": tk.BooleanVar(value=True)
        }
        self.mock_view.chunk_combo.current.return_value = 0
        
        self.logic = UILogic(self.mock_view, self.root)
        self.logic.session = MagicMock()
        self.logic.session.chunks = [MagicMock()]
        self.logic.session.chunks[0].chunk_id = 1
        self.logic.session.get_chunk_by_signature.return_value = self.logic.session.chunks[0]
        
        # Mock UI methods
        self.logic.validate_live = MagicMock()
        self.logic.on_save_chunk_clicked = MagicMock()
        self.root.after = MagicMock()

    def tearDown(self):
        self.root.destroy()

    @patch('ui.logic.queue_handler.pop_translation')
    @patch('ui.logic.session_manager.get_session_manager')
    @patch('ui.logic.local_translator.auto_correct_english')
    def test_poll_queue_triggers_auto_correct(self, mock_correct, mock_sm, mock_pop):
        mock_pop.return_value = {'translation': '@@CHUNK_SIGNATURE=123@@\n[1] Hello'}
        mock_sm.return_value.acquire_chunk.return_value = True
        mock_sm.return_value.can_initiate_final_save.return_value = False
        
        # Simulated translations in the UI
        self.mock_view.txt_translation.get.return_value = "[1] Hello"
        
        # 1st cget: "FAILED: English characters" (triggers auto-correction)
        # 2nd cget: "PASSED" (triggers save)
        self.mock_view.lbl_status.cget.side_effect = [
            "Validation FAILED: English characters detected",
            "Validation PASSED"
        ]
        
        mock_correct.return_value = "[1] مرحبا"
        
        self.logic.polling_active = True
        self.logic._poll_queue()
        
        # Verify auto corrector was called
        mock_correct.assert_called_once_with("[1] Hello")
        
        # Verify validate_live was called 3 times (on_chunk_selected, initial drop, after correction)
        self.assertEqual(self.logic.validate_live.call_count, 3)
        
        # Verify auto-save was triggered after successful correction
        self.logic.on_save_chunk_clicked.assert_called_once()
        
if __name__ == '__main__':
    unittest.main()
