#!/usr/bin/python

import os.path
import operator
import time
from multiprocessing import Pool
import argparse
import sys

class SameGameBoard(list):
    def __str__(self):
        # This is pretty ugly and probably merits a rewrite at some point.
        width = len(self)
        column_width = len(str(width))+1
        formatter = '%' + str(column_width) + 's'
        r = ' '*len(str(width)) + ''.join(formatter % str(i) for i in xrange(1, len(self)+1))+'\n'
        for i in zip(xrange(len(self), 0, -1), self):
            num = str(i[0])
            r += str(i[0]) + ' '*(len(str(width)) - len(num)) + ''.join([formatter % (str(j) if j else '*') for j in i[1]])+'\n'
        return r[:-1]

    def size(self):
        if not hasattr(self, '_size'):
            self._size = len(self)**2

        return self._size

    def copy(self):
        return SameGameBoard([list(i) for i in self])

    def occupied(self):
        return self.size() - sum(i.count(None) for i in self)

    def transpose(self):
        return SameGameBoard([[self[i][j] for i in xrange(len(self))] for j in xrange(len(self))])

    def collapse_columns(self):
        t = self.transpose()
        t.sort(key=lambda x: not any(x))
        for i in t:
            i.sort(key=lambda x: x is not None)
        return t.transpose()
    
    def collapse_rows(self):
        return SameGameBoard(sorted(self, key=lambda x: not any(x)))

    def collapse(self):
        return self.collapse_rows().collapse_columns()

    def _chain_length(self, row, column, board):
        color = board[row][column]
        count = 1

        board[row][column] = None
        
        if column < len(board)-1 and board[row][column+1] == color:
            count += self._chain_length(row, column+1, board)

        if row < len(board)-1 and board[row+1][column] == color:
            count += self._chain_length(row+1, column, board)
            
        if column > 0 and board[row][column-1] == color:
            count += self._chain_length(row, column-1, board)
    
        if row > 0 and board[row-1][column] == color:
            count += self._chain_length(row-1, column, board)
            
        return count

    def chain_length(self, row, column):
        return -1 if self[row][column] is None else self._chain_length(row, column, self.copy())

    def remove_chain(self, row, column):
        return -1 if self[row][column] is None else self._chain_length(row, column, self)

    def end_game(self):
        for i in xrange(len(self)-1, 0, -1):
            for j in xrange(len(self)):
                if self.chain_length(i, j) > 2:
                    return False
        return True

    def translate_coords(self, x, y):
        '''Translate coordinates with (1,1) being the bottom left
corner to our internal coordinate system.'''
        return (len(self) - x, y - 1)

    def inverse_translate_coords(self, x, y):
        return (len(self) - x, y + 1)

    def available_moves(self):
        '''Determines the possible moves for this board, along with
how many tiles each move will remove from the board.'''
        working_board = self.copy()
        queue = []
        for i in xrange(len(working_board)-1, 0, -1):
            for j in xrange(len(working_board)):
                removed = working_board.chain_length(i, j)
                if removed > 2:
                    queue.append(((i, j), removed))
                    working_board.remove_chain(i, j)
        return queue

    def isolated_tiles(self):
        '''Return the isolated tiles.'''
        working_board = self.copy()
        queue = []
        for i in xrange(len(working_board)-1, 0, -1):
            for j in xrange(len(working_board)):
                removed = working_board.chain_length(i, j)
                if 0 < removed < 3:
                    queue.append(((i, j), removed))
                    working_board.remove_chain(i, j)
        return queue

def _remove_and_collapse(move_board):
    move_board[1].remove_chain(*move_board[0][0])
    return move_board[1].collapse()

def _nonisolated_tiles(board):
    return board.size() - len(board.isolated_tiles())

# NOTE: These don't belong to a class because Python has issues
#       serializing instance methods of classes for use with the
#       multiprocessing module.
def _combined_core(_board, pool, w1=.2, w2=.8):
    '''Let f be as defined in _best_first_search_core. Let g be as
defined in _best_first_search_alt_core. This function maximizes
w1*f(x) + w2*g(x).'''
    moves = _board.available_moves()
    if not moves:
        return None

    boards = [_board.copy() for i in moves]
    boards = pool.map(_remove_and_collapse, zip(moves, boards))
    clusters = pool.map(_nonisolated_tiles, boards)
    moves_with_sums = [(m[0], w1*m[1] + w2*c) if m else (None, -1) for m, c in zip(moves, clusters)]

    return max(moves_with_sums, key=operator.itemgetter(1))

def _best_first_search_alt_core(_board):
    '''Given a tile t, we will say that t is isolated if t cannot
currently be removed from the board by a legal move. Let g : S -> Z be
defined by g(x) = |{t in x : t is NOT an isolated tile}|. This
function maximizes g(x) at each turn.'''
    moves = _board.available_moves()
    if not moves:
        return None
    boards = [_board.copy() for i in moves]
    for move, board in zip(moves, boards):
        board.remove_chain(*move[0])
    boards = [i.collapse() for i in boards]
    clusters = [(m[0], b.size() - len(b.isolated_tiles())) for m, b in zip(moves, boards)]

    return max(clusters, key=operator.itemgetter(1))

def _best_first_search_core(board):
    '''Define S as the space of SameGame boards. Given a board B in S,
define ||B|| to be the number of tiles on the board. Let f : S -> N be
defined by f(x) = ||x||. This function minimizes f(x) at each turn.'''
    moves = board.available_moves()
    if not moves:
        return None
    return max(moves, key=operator.itemgetter(1))

def _parallelize(board, pool, alg=_best_first_search_core):
    '''Splits the board into four segments and performs the supplied
heuristic on each.'''
    even = len(board) % 2 == 0
    size = (len(board)/2) if even else (len(board)/2 + 1) # size of each subsquare
    shift = size if even else (size-1) # translation
    boards = []

    boards.append(SameGameBoard([i[:size] for i in board[:size]]))
    boards.append(SameGameBoard([i[shift:] for i in board[:size]]))
    boards.append(SameGameBoard([i[:size] for i in board[shift:]]))
    boards.append(SameGameBoard([i[shift:] for i in board[shift:]]))

    processed = pool.map(alg, boards)
    results = []

    # Adjust the coordinates for the larger board
    if processed[0] is not None:
        results.append(processed[0])
    if processed[1] is not None:
        results.append(((processed[1][0][0], processed[1][0][1]+shift), processed[1][1]))
    if processed[2] is not None:
        results.append(((processed[2][0][0]+shift, processed[2][0][1]), processed[2][1]))
    if processed[3] is not None:
        results.append(((processed[3][0][0]+shift, processed[3][0][1]+shift), processed[3][1]))

    if not results:
        return alg(board)
    return max(results, key=operator.itemgetter(1))

class SameGame(object):
    def print_welcome(self):
        print "Welcome to Chainshot!"
        print "====================="

    def print_rules(self):
        print
        print 'Rules'
        print '====='
        print '''Your goal is to clear the board while scoring as many points
as possible along the way. You can only remove groups of three
or more tiles connected either vertically or horizontally by
entering the coordinates of one of the tiles within the group.
When you remove a tile, the tiles above it will fall down to
fill in the gap. When a column is cleared, any columns to the
right will be shifted left in order to fill in the gap. The
more tiles you remove in a single move, the more you score.
In particular, your score is calculated as (n-2)^2, where n
is the number of tiles removed from the board. Coordinates
should be entered as: x y. For example, 5 2 corresponds to
(5, 2). The bottom left corner is (1, 1).'''
        print

    def get_menu_choice(self, choices):
        for i in enumerate(choices):
            print "%d) %s" % (i[0]+1, i[1])
        print
        try:
            choice = int(raw_input('What would you like to do? '))
            if 0 < choice and choice <= len(choices):
                return choice
        except:
            pass

        print "I'm sorry, that wasn't a valid choice. Try something else."
        return self.get_menu_choice(choices)

    def get_move(self):
        raw = raw_input('Enter a move: ')
        try:
            move = [int(i) for i in raw.split(' ')]
            for i in move:
                if i < 0 or i > len(self.board):
                    raise

            if self.board.chain_length(*self.board.translate_coords(*move)) < 3:
                raise
            
            return move
        except:
            print 'This move is invalid. Please try again.'

        return self.get_move()

    def best_first_search(self, board_path, alg):
        '''Best-first search using the heuristic of most tiles removed.'''
        self.board = SameGameBoard([list(i.strip()) for i in open(board_path, 'r').readlines()])
        if not self.args.quiet:
            print self.board

        score = 0
        moves = []

        start = time.clock()
        while not self.board.end_game():     
            best = alg(self.board)
            moves.append(best[0])
            score += (self.board.remove_chain(*best[0])-2)**2
            self.board = self.board.collapse()
            if not self.args.quiet:
                print
                print self.board
        elapsed = time.clock() - start

        if not self.args.quiet:
            print
        unoccupied = self.board.size() - self.board.occupied()
        percentage = int(float(unoccupied)/self.board.size()*100)

        if self.args.quiet:
            print 'time: %.3s, clearance: %d/%d (%d%%), moves: %d, score: %d' % (elapsed,
                                                                                 unoccupied,
                                                                                 self.board.size(),
                                                                                 percentage,
                                                                                 len(moves),
                                                                                 score)
        else:
            print 'Game over! Took %.3f seconds.' % elapsed
            print 'Cleared %d/%d tiles (%d%%) in %d moves for a score of %d.' % (unoccupied,
                                                                                 self.board.size(),
                                                                                 percentage,
                                                                                 len(moves),
                                                                                 score)
            print [self.board.inverse_translate_coords(*i) for i in moves]
            print

    def play_game(self, board_path):
        self.board = SameGameBoard([list(i.strip()) for i in open(board_path, 'r').readlines()])
        print self.board
        score = 0
        while not self.board.end_game():
            move = self.get_move()
            result = (self.board.remove_chain(*self.board.translate_coords(*move)) - 2)**2
            print 'Your move (%d, %d) increased your score by %d' % (move[0], move[1], result)
            score += result
            print 'Score: %d' % score
            self.board = self.board.collapse()
            print self.board
            
        print
        print 'Game over! Your final score was %d.' % score
        print
            
    def get_board(self):
        board = raw_input('Please enter the path to the board: ')
        if os.path.isfile(board):
            return board
        else:
            print "I'm sorry, but that path was invalid."
            return self.get_board()         

    def chainshot(self):
        parallel_pool = Pool(4)
        algs = [_best_first_search_core, _best_first_search_alt_core, lambda x: _combined_core(x, parallel_pool)]
        parser = argparse.ArgumentParser(description='A board must be specified for these options to take effect.')
        parser.add_argument("board", nargs='?', default=None,
                            help="path to the board")
        parser.add_argument("-q", "--quiet", action="store_true",
                            help="suppress printing of boards and move lists")
        parser.add_argument("-a", "--ai", type=int, choices=[1, 2, 3],
                            help="the AI with which to play: either 1, 2, or 3")
        parser.add_argument("-p", "--parallel", action="store_true",
                            help="parallelize the search (much faster, but less board clearance), only affects the non-combined searches (i.e., 1 and 2)")
        self.args = parser.parse_args()

        if self.args.board:
            alg = (lambda x: _parallelize(x, parallel_pool, algs[self.args.ai-1])) if self.args.parallel and self.args.ai != 3 else algs[self.args.ai-1]
            self.best_first_search(self.args.board, alg)
            return

        while True:
            self.print_welcome()
            choice = self.get_menu_choice(['Human Play', 'AI Play', 'Rules', 'Exit'])
            if choice == 1:
                self.play_game(self.get_board())
            elif choice == 2:
                alg_choice = self.get_menu_choice(['Best first search (maximize taken)',
                                                   'Best first search (maximize clusters)',
                                                   'Combined best first search (1 + 2)'])
                parallel_choice = self.get_menu_choice(['Sequential', 'Parallel'])
                alg = (lambda x: _parallelize(x, parallel_pool, algs[alg_choice-1])) if parallel_choice == 2 and alg_choice != 3 else algs[alg_choice-1]
                self.best_first_search(self.get_board(), alg)
            elif choice == 3:
                self.print_rules()
            else:
                break

if __name__ == '__main__':
    sg = SameGame()
    sg.chainshot()
