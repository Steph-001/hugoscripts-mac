#!/usr/bin/env python3
"""
Chess Game Analyzer with Stockfish
===================================

Analyzes chess games in PGN format using Stockfish engine, annotating 
moves with standard chess symbols (?!, ?, ??) and generating detailed 
accuracy reports using Lichess formulas.

Author: Your Name
Version: 1.0
Last Updated: 2025-10-26

Requirements:
    - Python 3.7+
    - python-chess library: pip install chess
    - Stockfish binary installed and accessible

Output:
    - Annotated PGN file with move annotations
    - Detailed analysis report with accuracy statistics
"""

import chess
import chess.engine
import chess.pgn
import math
import argparse
import sys
from pathlib import Path

# ---------------- DEFAULT CONFIG ----------------
DEFAULT_STOCKFISH_PATH = "/usr/local/bin/stockfish-bin"
DEFAULT_DEPTH = 25
DEFAULT_TOP_MOVES = 5

# Annotatiron thresholds (in pawns)
DEFAULT_THRESH_INACCURACY = 0.4
DEFAULT_THRESH_MISTAKE = 0.8
DEFAULT_THRESH_BLUNDER = 1.8

# NAG mapping - ONLY negative annotations
ANNOTATIONS = {
    "?!": 6,  # dubious/inaccuracy
    "?": 2,   # mistake
    "??": 4,  # blunder
}

# Reverse mapping for reporting
NAG_NAMES = {
    6: "Inaccuracies (?!)",
    2: "Mistakes (?)",
    4: "Blunders (??)",
}

# ---------------- FUNCTIONS ----------------

def centipawns_to_win_percent(centipawns):
    """Convert centipawns to win percentage using Lichess formula."""
    return 50 + 50 * (2 / (1 + math.exp(-0.00368208 * centipawns)) - 1)

def calculate_move_accuracy(win_percent_before, win_percent_after):
    """Calculate move accuracy using Lichess formula."""
    win_percent_loss = win_percent_before - win_percent_after
    if win_percent_loss < 0:
        win_percent_loss = 0  # Can't gain accuracy beyond 100%
    accuracy = 103.1668 * math.exp(-0.04354 * win_percent_loss) - 3.1669
    return max(0, min(100, accuracy))  # Clamp between 0 and 100

def evaluate_position(engine, board, depth):
    """Return evaluation in pawns from White's perspective."""
    info = engine.analyse(board, chess.engine.Limit(depth=depth))
    score = info["score"].white()  # Always from White's perspective
    
    if isinstance(score, chess.engine.Cp):
        return score.score() / 100.0
    elif isinstance(score, chess.engine.Mate):
        mate_value = score.mate()
        return 100.0 if mate_value > 0 else -100.0
    else:
        return None

def get_top_moves(engine, board, depth, n=5):
    """Return top n moves with their evaluations from current player's perspective."""
    info = engine.analyse(board, chess.engine.Limit(depth=depth), multipv=n)
    top_moves = []
    
    entries = info if isinstance(info, list) else [info]
    
    for entry in entries:
        if "pv" in entry and entry["pv"]:
            move = entry["pv"][0]
            score = entry["score"].pov(board.turn)  # From current player's perspective
            
            if isinstance(score, chess.engine.Cp):
                eval_score = score.score() / 100.0
            elif isinstance(score, chess.engine.Mate):
                mate_value = score.mate()
                eval_score = 100.0 if mate_value > 0 else -100.0
            else:
                continue
                
            top_moves.append((move, eval_score))
    
    return top_moves

def clean_game_annotations(game):
    """Remove all existing comments and NAGs from the game."""
    # Clean the root game node
    game.comment = ""
    
    # Clean all nodes in the game tree
    def clean_node(node):
        node.comment = ""
        node.nags.clear()
        for variation in node.variations:
            clean_node(variation)
    
    clean_node(game)
    
    # Keep only main line variations
    def keep_mainline_only(node):
        if node.variations:
            main_variation = node.variations[0]
            node.variations = [main_variation]
            keep_mainline_only(main_variation)
    
    keep_mainline_only(game)
    
    return game

def annotate_game(game, engine, depth, top_moves, thresh_inac, thresh_mistake, thresh_blunder):
    """Annotate the game with Stockfish evaluations - ONLY negative annotations."""
    board = game.board()
    node = game
    move_number = 1
    
    # Statistics tracking - only negative annotations
    stats = {
        'white': {6: 0, 2: 0, 4: 0, 'moves': 0, 'total_accuracy': 0.0, 'accuracy_count': 0},
        'black': {6: 0, 2: 0, 4: 0, 'moves': 0, 'total_accuracy': 0.0, 'accuracy_count': 0},
        'total_moves': 0
    }
    
    annotated_moves = []
    
    print(f"Analyzing game... (this may take a while)")
    
    # Process each move in the main line
    while node.variations:
        current_node = node.variations[0]
        move = current_node.move
        
        # Get move notation before playing it
        move_notation = board.san(move)
        current_player = 'white' if board.turn else 'black'  # Player who is about to move
        
        # Count all moves
        stats[current_player]['moves'] += 1
        stats['total_moves'] += 1
        
        # Get evaluation before the move (in centipawns from White's perspective)
        eval_before = evaluate_position(engine, board, depth)
        
        # Convert to win percentage from current player's perspective
        if eval_before is not None:
            cp_before = eval_before * 100  # Convert back to centipawns
            if current_player == 'black':
                cp_before = -cp_before  # Flip for black's perspective
            win_percent_before = centipawns_to_win_percent(cp_before)
        else:
            win_percent_before = None
        
        # Get top moves for finding the best alternative (for reporting)
        top_move_list = get_top_moves(engine, board, depth, top_moves)
        
        # Play the move
        board.push(move)
        
        # Get evaluation after the move
        eval_after = evaluate_position(engine, board, depth)
        
        # Convert to win percentage from current player's perspective
        if eval_after is not None:
            cp_after = eval_after * 100  # Convert back to centipawns
            if current_player == 'black':
                cp_after = -cp_after  # Flip for black's perspective
            win_percent_after = centipawns_to_win_percent(cp_after)
        else:
            win_percent_after = None
        
        # Calculate move accuracy using Lichess formula
        move_accuracy = None
        if win_percent_before is not None and win_percent_after is not None:
            move_accuracy = calculate_move_accuracy(win_percent_before, win_percent_after)
            stats[current_player]['total_accuracy'] += move_accuracy
            stats[current_player]['accuracy_count'] += 1
        
        # Clear any existing NAGs
        current_node.nags.clear()
        
        # Skip annotating first few opening moves to avoid nonsensical annotations
        if move_number > 2:
            # Calculate evaluation change from the moving player's perspective
            if eval_before is not None and eval_after is not None:
                # For White moves: positive change = good for White
                # For Black moves: negative change in White's eval = good for Black
                if current_player == 'white':
                    eval_change = eval_after - eval_before
                else:  # black player
                    eval_change = eval_before - eval_after
                
                annotation = None
                
                # ONLY apply negative annotations for bad moves (negative eval_change)
                if eval_change <= -thresh_blunder:
                    current_node.nags.add(ANNOTATIONS["??"])
                    stats[current_player][ANNOTATIONS["??"]] += 1
                    annotation = "??"
                elif eval_change <= -thresh_mistake:
                    current_node.nags.add(ANNOTATIONS["?"])
                    stats[current_player][ANNOTATIONS["?"]] += 1
                    annotation = "?"
                elif eval_change <= -thresh_inac:
                    current_node.nags.add(ANNOTATIONS["?!"])
                    stats[current_player][ANNOTATIONS["?!"]] += 1
                    annotation = "?!"
                
                # Track annotated moves for detailed report
                if annotation:
                    annotated_moves.append({
                        'move_number': move_number,
                        'player': current_player.capitalize(),
                        'move': move_notation,
                        'annotation': annotation,
                        'eval_change': eval_change,
                        'move_accuracy': move_accuracy
                    })
        
        # Move to next node
        node = current_node
        if board.turn == chess.WHITE:  # Just finished Black's move
            move_number += 1
    
    return game, stats, annotated_moves

def generate_report(game, stats, annotated_moves, depth, thresh_inac, thresh_mistake, thresh_blunder):
    """Generate a detailed analysis report."""
    white_player = game.headers.get('White', 'White')
    black_player = game.headers.get('Black', 'Black')
    
    report_lines = []
    report_lines.append("=" * 60)
    report_lines.append("CHESS GAME ANALYSIS REPORT")
    report_lines.append("=" * 60)
    report_lines.append("")
    
    # Game information
    report_lines.append("GAME INFORMATION:")
    report_lines.append(f"White: {white_player}")
    report_lines.append(f"Black: {black_player}")
    report_lines.append(f"Event: {game.headers.get('Event', 'Unknown')}")
    report_lines.append(f"Date: {game.headers.get('Date', 'Unknown')}")
    report_lines.append(f"Result: {game.headers.get('Result', '*')}")
    report_lines.append("")
    
    # Analysis settings
    report_lines.append("ANALYSIS SETTINGS:")
    report_lines.append(f"Engine: Stockfish")
    report_lines.append(f"Depth: {depth}")
    report_lines.append(f"Accuracy calculation: Lichess formula")
    report_lines.append(f"Inaccuracy threshold: {thresh_inac} pawns")
    report_lines.append(f"Mistake threshold: {thresh_mistake} pawns")
    report_lines.append(f"Blunder threshold: {thresh_blunder} pawns")
    report_lines.append("")
    
    # Summary statistics
    report_lines.append("SUMMARY STATISTICS:")
    report_lines.append(f"Total moves analyzed: {stats['total_moves']}")
    report_lines.append(f"White moves: {stats['white']['moves']}")
    report_lines.append(f"Black moves: {stats['black']['moves']}")
    report_lines.append("")
    
    # Detailed statistics by player
    for player_key, player_name in [('white', white_player), ('black', black_player)]:
        report_lines.append(f"{player_name.upper()} STATISTICS:")
        player_stats = stats[player_key]
        total_annotations = sum(player_stats[nag] for nag in [6, 2, 4])
        
        if total_annotations > 0:
            for nag, description in NAG_NAMES.items():
                count = player_stats[nag]
                if count > 0:
                    percentage = (count / player_stats['moves']) * 100 if player_stats['moves'] > 0 else 0
                    report_lines.append(f"  {description}: {count} ({percentage:.1f}%)")
            
            # Calculate error rate (percentage of moves with negative annotations)
            error_rate = (total_annotations / player_stats['moves']) * 100 if player_stats['moves'] > 0 else 0
            report_lines.append(f"  Error rate: {error_rate:.1f}% ({total_annotations}/{player_stats['moves']} moves)")
        else:
            report_lines.append("  No errors found")
        
        # Average accuracy
        if player_stats['accuracy_count'] > 0:
            avg_accuracy = player_stats['total_accuracy'] / player_stats['accuracy_count']
            report_lines.append(f"  Average Move Accuracy: {avg_accuracy:.1f}%")
        else:
            report_lines.append("  Average Move Accuracy: N/A")
        
        report_lines.append("")
    
    # Comparison
    if stats['white']['moves'] > 0 and stats['black']['moves'] > 0:
        # Compare using average accuracy and error rates
        white_accuracy = (stats['white']['total_accuracy'] / stats['white']['accuracy_count']) if stats['white']['accuracy_count'] > 0 else 0
        black_accuracy = (stats['black']['total_accuracy'] / stats['black']['accuracy_count']) if stats['black']['accuracy_count'] > 0 else 0
        
        white_errors = sum(stats['white'][nag] for nag in [6, 2, 4])
        black_errors = sum(stats['black'][nag] for nag in [6, 2, 4])
        white_error_rate = (white_errors / stats['white']['moves']) * 100
        black_error_rate = (black_errors / stats['black']['moves']) * 100
        
        report_lines.append("COMPARISON:")
        report_lines.append(f"White average accuracy: {white_accuracy:.1f}%")
        report_lines.append(f"Black average accuracy: {black_accuracy:.1f}%")
        report_lines.append(f"White error rate: {white_error_rate:.1f}%")
        report_lines.append(f"Black error rate: {black_error_rate:.1f}%")
        
        if white_accuracy > black_accuracy:
            report_lines.append(f"White played more accurately (by {white_accuracy - black_accuracy:.1f}%)")
        elif black_accuracy > white_accuracy:
            report_lines.append(f"Black played more accurately (by {black_accuracy - white_accuracy:.1f}%)")
        else:
            report_lines.append("Both players had similar accuracy")
        report_lines.append("")
    
    # Detailed move-by-move annotations (ONLY errors)
    if annotated_moves:
        report_lines.append("ERRORS FOUND:")
        report_lines.append("-" * 50)
        
        for move_info in annotated_moves:
            move_num_str = f"{move_info['move_number']}." if move_info['player'] == 'White' else f"{move_info['move_number']}..."
            accuracy_str = f" (Accuracy: {move_info['move_accuracy']:.1f}%)" if move_info.get('move_accuracy') is not None else ""
            
            report_lines.append(f"{move_num_str} {move_info['move']} {move_info['annotation']} "
                              f"({move_info['player']}) - Lost: {abs(move_info['eval_change']):.2f} pawns{accuracy_str}")
    else:
        report_lines.append("No errors found - excellent play!")
    
    return "\n".join(report_lines)

# ---------------- ARGUMENT PARSING ----------------

def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description='Analyze chess games using Stockfish engine and generate annotated PGN files with accuracy reports.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  Basic usage:
    %(prog)s game.pgn
  
  Custom output files:
    %(prog)s game.pgn -o annotated.pgn -r report.txt
  
  Custom analysis depth (deeper = slower but more accurate):
    %(prog)s game.pgn --depth 30
  
  Adjust annotation thresholds:
    %(prog)s game.pgn --inaccuracy 0.3 --mistake 0.6 --blunder 1.5
  
  Custom Stockfish location:
    %(prog)s game.pgn --engine /path/to/stockfish

Notes:
  - Higher depth = more accurate analysis but slower (15-30 is typical)
  - Thresholds are in pawns (centipawns / 100)
  - First 2 moves are skipped to avoid opening book annotations
  - Uses Lichess formulas for accuracy calculation
        '''
    )
    
    # Required arguments
    parser.add_argument(
        'input',
        type=str,
        help='Input PGN file containing the chess game to analyze'
    )
    
    # Optional arguments
    parser.add_argument(
        '-o', '--output',
        type=str,
        default=None,
        help='Output PGN file for annotated game (default: annotated_<input>)'
    )
    
    parser.add_argument(
        '-r', '--report',
        type=str,
        default=None,
        help='Output file for analysis report (default: analysis_report.txt)'
    )
    
    parser.add_argument(
        '-e', '--engine',
        type=str,
        default=DEFAULT_STOCKFISH_PATH,
        help=f'Path to Stockfish binary (default: {DEFAULT_STOCKFISH_PATH})'
    )
    
    parser.add_argument(
        '-d', '--depth',
        type=int,
        default=DEFAULT_DEPTH,
        help=f'Analysis depth for Stockfish (default: {DEFAULT_DEPTH})'
    )
    
    parser.add_argument(
        '--top-moves',
        type=int,
        default=DEFAULT_TOP_MOVES,
        help=f'Number of top moves to consider (default: {DEFAULT_TOP_MOVES})'
    )
    
    parser.add_argument(
        '--inaccuracy',
        type=float,
        default=DEFAULT_THRESH_INACCURACY,
        help=f'Threshold for inaccuracy (?!) in pawns (default: {DEFAULT_THRESH_INACCURACY})'
    )
    
    parser.add_argument(
        '--mistake',
        type=float,
        default=DEFAULT_THRESH_MISTAKE,
        help=f'Threshold for mistake (?) in pawns (default: {DEFAULT_THRESH_MISTAKE})'
    )
    
    parser.add_argument(
        '--blunder',
        type=float,
        default=DEFAULT_THRESH_BLUNDER,
        help=f'Threshold for blunder (??) in pawns (default: {DEFAULT_THRESH_BLUNDER})'
    )
    
    parser.add_argument(
        '-v', '--version',
        action='version',
        version='%(prog)s 1.0'
    )
    
    return parser.parse_args()

# ---------------- MAIN ----------------

def main():
    # Parse arguments
    args = parse_arguments()
    
    # Set default output filenames if not provided
    input_path = Path(args.input)
    if args.output is None:
        output_pgn = input_path.parent / f"annotated_{input_path.name}"
    else:
        output_pgn = Path(args.output)
    
    if args.report is None:
        report_file = input_path.parent / "analysis_report.txt"
    else:
        report_file = Path(args.report)
    
    try:
        # Check if input file exists
        if not input_path.exists():
            print(f"Error: Input file not found: {args.input}")
            sys.exit(1)
        
        # Check if Stockfish exists
        if not Path(args.engine).exists():
            print(f"Error: Stockfish engine not found at: {args.engine}")
            print("Please install Stockfish or specify the correct path with --engine")
            sys.exit(1)
        
        print(f"Reading PGN file: {args.input}")
        with open(args.input, 'r', encoding='utf-8') as f:
            game = chess.pgn.read_game(f)
        
        if game is None:
            print(f"Error: Could not read game from {args.input}")
            sys.exit(1)
        
        print(f"Game loaded: {game.headers.get('White', '?')} vs {game.headers.get('Black', '?')}")
        print(f"Analysis settings: Depth={args.depth}, Thresholds=(?!:{args.inaccuracy}, ?:{args.mistake}, ??:{args.blunder})")
        
        # Clean all existing annotations
        game = clean_game_annotations(game)
        
        print("Starting Stockfish analysis...")
        
        # Annotate game with Stockfish
        with chess.engine.SimpleEngine.popen_uci(args.engine) as engine:
            annotated_game, stats, annotated_moves = annotate_game(
                game, engine, args.depth, args.top_moves,
                args.inaccuracy, args.mistake, args.blunder
            )
        
        # Generate report
        print("Generating analysis report...")
        report = generate_report(
            annotated_game, stats, annotated_moves,
            args.depth, args.inaccuracy, args.mistake, args.blunder
        )
        
        # Write the report
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(report)
        
        # Write the clean annotated game
        print(f"Writing annotated game to: {output_pgn}")
        with open(output_pgn, "w", encoding="utf-8") as f:
            print(annotated_game, file=f, end="\n\n")
        
        print(f"\n{'='*50}")
        print("Analysis complete!")
        print(f"{'='*50}")
        print(f"Annotated PGN: {output_pgn}")
        print(f"Analysis report: {report_file}")
        
        # Print quick summary to terminal
        total_errors = sum(stats['white'][nag] + stats['black'][nag] for nag in [6, 2, 4])
        print(f"\nQuick Summary:")
        print(f"  Total moves analyzed: {stats['total_moves']}")
        print(f"  Total errors found: {total_errors}")
        
        white_accuracy = (stats['white']['total_accuracy'] / stats['white']['accuracy_count']) if stats['white']['accuracy_count'] > 0 else 0
        black_accuracy = (stats['black']['total_accuracy'] / stats['black']['accuracy_count']) if stats['black']['accuracy_count'] > 0 else 0
        print(f"  White accuracy: {white_accuracy:.1f}%")
        print(f"  Black accuracy: {black_accuracy:.1f}%")
        
    except FileNotFoundError as e:
        print(f"Error: File not found - {e}")
        sys.exit(1)
    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
