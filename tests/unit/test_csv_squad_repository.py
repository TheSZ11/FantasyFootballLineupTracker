"""
Unit tests for CSVSquadRepository.

Tests the CSV parsing logic for Fantrax exports with complex format
including mixed sections and different column structures.
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch

from src.lineup_tracker.repositories.csv_squad_repository import CSVSquadRepository
from src.lineup_tracker.domain.models import Squad, Player, Team
from src.lineup_tracker.domain.enums import Position, PlayerStatus
from src.lineup_tracker.domain.exceptions import SquadLoadError, SquadValidationError, CSVParsingError


@pytest.mark.unit
class TestCSVSquadRepository:
    """Test the CSV squad repository implementation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.repository = CSVSquadRepository()
    
    def test_load_squad_success(self, sample_csv_data):
        """Test successful squad loading from CSV."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(sample_csv_data)
            f.flush()
            
            try:
                squad = self.repository.load_squad(f.name)
                
                assert isinstance(squad, Squad)
                assert squad.total_count == 3
                assert squad.active_count == 2
                assert squad.reserve_count == 1
                
                # Check player details
                players = squad.players
                goalkeeper = next(p for p in players if p.position == Position.GOALKEEPER)
                forward = next(p for p in players if p.position == Position.FORWARD)
                midfielder = next(p for p in players if p.position == Position.MIDFIELDER)
                
                # Goalkeeper checks
                assert goalkeeper.name == "Test Goalkeeper"
                assert goalkeeper.team.name == "Liverpool"
                assert goalkeeper.team.abbreviation == "LIV"
                assert goalkeeper.status == PlayerStatus.ACTIVE
                assert goalkeeper.fantasy_points == 100.0
                assert goalkeeper.average_points == 8.0
                assert goalkeeper.age == 25
                
                # Forward checks
                assert forward.name == "Test Forward"
                assert forward.status == PlayerStatus.ACTIVE
                assert forward.fantasy_points == 150.0
                assert forward.average_points == 12.5
                assert forward.draft_percentage == "100"
                
                # Midfielder checks
                assert midfielder.name == "Test Midfielder"
                assert midfielder.team.name == "Arsenal"
                assert midfielder.status == PlayerStatus.RESERVE
                assert midfielder.fantasy_points == 75.0
                
            finally:
                os.unlink(f.name)
    
    def test_load_squad_file_not_found(self):
        """Test handling of missing squad file."""
        with pytest.raises(SquadLoadError) as exc_info:
            self.repository.load_squad("nonexistent_file.csv")
        
        assert "Squad file not found" in str(exc_info.value)
    
    def test_load_squad_empty_file(self):
        """Test handling of empty CSV file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("")  # Empty file
            f.flush()
            
            try:
                with pytest.raises(SquadValidationError) as exc_info:
                    self.repository.load_squad(f.name)
                
                assert "No valid players found" in str(exc_info.value)
            finally:
                os.unlink(f.name)
    
    def test_parse_csv_file(self, sample_csv_data):
        """Test CSV file parsing logic."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(sample_csv_data)
            f.flush()
            
            try:
                players = self.repository._parse_csv_file(f.name)
                
                assert len(players) == 3
                
                # Verify each player was parsed correctly
                player_names = {p.name for p in players}
                assert "Test Goalkeeper" in player_names
                assert "Test Forward" in player_names
                assert "Test Midfielder" in player_names
                
            finally:
                os.unlink(f.name)
    
    def test_create_player_from_row(self):
        """Test creating player from CSV row data."""
        headers = ["ID", "Pos", "Player", "Team", "Status", "Fantasy Points", 
                  "Average Fantasy Points per Game", "Age", "GP"]
        row_data = ["*test1*", "F", "Test Player", "LIV", "Act", "100.5", "8.5", "28", "15"]
        
        player = self.repository._create_player_from_row(row_data, headers, "Outfielder", 1)
        
        assert player is not None
        assert player.id == "*test1*"
        assert player.name == "Test Player"
        assert player.team.name == "Liverpool"
        assert player.team.abbreviation == "LIV"
        assert player.position == Position.FORWARD
        assert player.status == PlayerStatus.ACTIVE
        assert player.fantasy_points == 100.5
        assert player.average_points == 8.5
        assert player.age == 28
        assert player.games_played == 15
    
    def test_create_player_from_row_missing_data(self):
        """Test handling of missing or invalid data in rows."""
        headers = ["ID", "Player", "Team"]
        
        # Missing essential data
        invalid_row = ["", "", ""]
        player = self.repository._create_player_from_row(invalid_row, headers, "Outfielder", 1)
        assert player is None
        
        # Mismatched row length
        short_row = ["*test1*"]
        player = self.repository._create_player_from_row(short_row, headers, "Outfielder", 1)
        assert player is None
    
    def test_determine_position(self):
        """Test position determination logic."""
        # From position code
        assert self.repository._determine_position({"Pos": "G"}, "Outfielder") == Position.GOALKEEPER
        assert self.repository._determine_position({"Pos": "D"}, "Outfielder") == Position.DEFENDER
        assert self.repository._determine_position({"Pos": "M"}, "Outfielder") == Position.MIDFIELDER
        assert self.repository._determine_position({"Pos": "F"}, "Outfielder") == Position.FORWARD
        
        # From section when no position code
        assert self.repository._determine_position({"Pos": ""}, "Goalkeeper") == Position.GOALKEEPER
        assert self.repository._determine_position({"Pos": ""}, "Outfielder") == Position.MIDFIELDER
        
        # Unknown position code defaults to midfielder
        assert self.repository._determine_position({"Pos": "X"}, "Outfielder") == Position.MIDFIELDER
    
    def test_determine_status(self):
        """Test status determination logic."""
        assert self.repository._determine_status("Act") == PlayerStatus.ACTIVE
        assert self.repository._determine_status("ACT") == PlayerStatus.ACTIVE
        assert self.repository._determine_status("act") == PlayerStatus.ACTIVE
        
        assert self.repository._determine_status("Res") == PlayerStatus.RESERVE
        assert self.repository._determine_status("RES") == PlayerStatus.RESERVE
        assert self.repository._determine_status("res") == PlayerStatus.RESERVE
        
        # Unknown status defaults to reserve
        assert self.repository._determine_status("Unknown") == PlayerStatus.RESERVE
        assert self.repository._determine_status("") == PlayerStatus.RESERVE
    
    def test_safe_float_parse(self):
        """Test safe float parsing."""
        assert self.repository._safe_float_parse("10.5") == 10.5
        assert self.repository._safe_float_parse("0") == 0.0
        assert self.repository._safe_float_parse("") == 0.0
        assert self.repository._safe_float_parse("invalid") == 0.0
        assert self.repository._safe_float_parse("  15.5  ") == 15.5
    
    def test_safe_int_parse(self):
        """Test safe integer parsing."""
        assert self.repository._safe_int_parse("25") == 25
        assert self.repository._safe_int_parse("0") == 0
        assert self.repository._safe_int_parse("") is None
        assert self.repository._safe_int_parse("invalid") is None
        assert self.repository._safe_int_parse("  30  ") == 30
    
    def test_position_mappings(self):
        """Test position code mappings."""
        mappings = self.repository._position_mappings
        
        assert mappings['G'] == Position.GOALKEEPER
        assert mappings['D'] == Position.DEFENDER
        assert mappings['M'] == Position.MIDFIELDER
        assert mappings['F'] == Position.FORWARD
    
    def test_position_to_fantrax_code(self):
        """Test reverse position mapping."""
        assert self.repository._position_to_fantrax_code(Position.GOALKEEPER) == 'G'
        assert self.repository._position_to_fantrax_code(Position.DEFENDER) == 'D'
        assert self.repository._position_to_fantrax_code(Position.MIDFIELDER) == 'M'
        assert self.repository._position_to_fantrax_code(Position.FORWARD) == 'F'
    
    def test_save_squad(self, sample_squad):
        """Test saving squad to CSV."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            try:
                result = self.repository.save_squad(sample_squad, f.name)
                assert result is True
                
                # Verify file was created and has content
                assert os.path.exists(f.name)
                
                with open(f.name, 'r') as read_file:
                    content = read_file.read()
                    assert len(content) > 0
                    assert "Mohamed Salah" in content
                    assert "Backup Player" in content
                    
            finally:
                if os.path.exists(f.name):
                    os.unlink(f.name)
    
    def test_save_squad_error(self, sample_squad):
        """Test save error handling."""
        # Try to save to invalid path
        result = self.repository.save_squad(sample_squad, "/invalid/path/file.csv")
        assert result is False
    
    def test_squad_exists(self):
        """Test squad file existence check."""
        # Test with non-existent file
        assert self.repository.squad_exists("nonexistent.csv") is False
        
        # Test with existing file
        with tempfile.NamedTemporaryFile(delete=False) as f:
            try:
                assert self.repository.squad_exists(f.name) is True
            finally:
                os.unlink(f.name)
    
    def test_complex_csv_structure(self):
        """Test handling of complex CSV with multiple sections."""
        complex_csv = '''
"","Goalkeeper"
"ID","Pos","Player","Team","Status","Fantasy Points","Average Fantasy Points per Game","Age","GP"
"*gk1*","G","Goalkeeper One","LIV","Act","50.0","4.0","30","12"
"*gk2*","G","Goalkeeper Two","ARS","Res","25.0","2.0","22","8"

"","Outfielder"
"ID","Pos","Player","Team","Status","Fantasy Points","Average Fantasy Points per Game","Age","GP"
"*out1*","D","Defender One","LIV","Act","75.0","6.0","26","15"
"*out2*","M","Midfielder One","MCI","Act","100.0","8.0","28","18"
"*out3*","F","Forward One","CHE","Res","60.0","5.0","24","12"
        '''.strip()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(complex_csv)
            f.flush()
            
            try:
                squad = self.repository.load_squad(f.name)
                
                assert squad.total_count == 5
                
                # Check we have both goalkeepers and outfielders
                goalkeepers = [p for p in squad.players if p.position == Position.GOALKEEPER]
                outfielders = [p for p in squad.players if p.position != Position.GOALKEEPER]
                
                assert len(goalkeepers) == 2
                assert len(outfielders) == 3
                
                # Check different teams are handled
                teams = squad.get_teams()
                assert "Liverpool" in teams
                assert "Arsenal" in teams
                assert "Manchester City" in teams
                assert "Chelsea" in teams
                
            finally:
                os.unlink(f.name)
    
    def test_malformed_csv_lines(self):
        """Test handling of malformed CSV lines."""
        malformed_csv = '''
"","Goalkeeper"
"ID","Pos","Player","Team","Status"
"*good*","G","Good Player","LIV","Act"
This is not a valid CSV line
"*good2*","G","Another Good Player","ARS","Act"
        '''.strip()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(malformed_csv)
            f.flush()
            
            try:
                # Should not crash and should parse the valid lines
                squad = self.repository.load_squad(f.name)
                assert squad.total_count == 2
                
            finally:
                os.unlink(f.name)
    
    def test_log_squad_summary(self, sample_squad, caplog):
        """Test squad summary logging."""
        import logging
        caplog.set_level(logging.INFO)
        
        self.repository._log_squad_summary(sample_squad)
        
        # Check that summary information was logged
        log_messages = [record.message for record in caplog.records]
        
        assert any("Squad summary:" in msg for msg in log_messages)
        assert any("Total players: 2" in msg for msg in log_messages)
        assert any("Active players: 1" in msg for msg in log_messages)
        assert any("Reserve players: 1" in msg for msg in log_messages)
    
    def test_unicode_handling(self):
        """Test handling of Unicode characters in player names."""
        unicode_csv = '''
"","Outfielder"
"ID","Pos","Player","Team","Status","Fantasy Points","Average Fantasy Points per Game"
"*unicode*","M","José María Callejón","LIV","Act","80.0","6.5"
        '''.strip()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
            f.write(unicode_csv)
            f.flush()
            
            try:
                squad = self.repository.load_squad(f.name)
                assert squad.total_count == 1
                assert squad.players[0].name == "José María Callejón"
                
            finally:
                os.unlink(f.name)
    
    def test_edge_case_empty_sections(self):
        """Test handling of empty sections."""
        empty_sections_csv = '''
"","Goalkeeper"
"ID","Pos","Player","Team","Status"

"","Outfielder"
"ID","Pos","Player","Team","Status"
"*player1*","M","Only Player","LIV","Act"
        '''.strip()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(empty_sections_csv)
            f.flush()
            
            try:
                squad = self.repository.load_squad(f.name)
                assert squad.total_count == 1
                assert squad.players[0].name == "Only Player"
                
            finally:
                os.unlink(f.name)
    
    @patch('src.lineup_tracker.utils.team_mappings.get_full_team_name')
    def test_team_mapping_integration(self, mock_team_mapping):
        """Test integration with team mapping utility."""
        mock_team_mapping.return_value = "Mocked Team Name"
        
        headers = ["ID", "Player", "Team", "Status"]
        row_data = ["*test*", "Test Player", "TEST", "Act"]
        
        player = self.repository._create_player_from_row(row_data, headers, "Outfielder", 1)
        
        # The player should use the mocked team name
        if player:
            assert player.team.name == "Mocked Team Name"
            assert player.team.abbreviation == "TEST"
            mock_team_mapping.assert_called_once_with("TEST")
    
    def test_performance_with_large_csv(self):
        """Test performance with larger CSV files."""
        # Create a larger CSV with 50 players
        large_csv_lines = ['"","Outfielder"']
        large_csv_lines.append('"ID","Pos","Player","Team","Status","Fantasy Points","Average Fantasy Points per Game"')
        
        for i in range(50):
            large_csv_lines.append(f'"*player{i}*","M","Player {i}","LIV","Act","100.0","8.0"')
        
        large_csv = '\n'.join(large_csv_lines)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(large_csv)
            f.flush()
            
            try:
                import time
                start_time = time.time()
                
                squad = self.repository.load_squad(f.name)
                
                end_time = time.time()
                processing_time = end_time - start_time
                
                assert squad.total_count == 50
                assert processing_time < 1.0  # Should process quickly
                
            finally:
                os.unlink(f.name)
