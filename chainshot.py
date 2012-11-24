#!/usr/bin/python

import os.path
import operator
import time
from multiprocessing import Pool

class SameGameBoard(list):
    # TODO: Print row and column numbers
    def __str__(self):
        r = ''
        for i in self:
            r += ''.join([str(j) if j else '*' for j in i])+'\n'
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
        return (len(self) - x, y - 1)

    def inverse_translate_coords(self, x, y):
        return (len(self) - x, y + 1)

# NOTE: These don't belong to a class because Python has issues
#       serializing instance methods of classes for use with the
#       multiprocessing module.
def _best_first_search_core(board):
    '''Return the best move for the supplied board.'''
    working_board = board.copy()
    queue = []
    for i in xrange(len(working_board)-1, 0, -1):
        for j in xrange(len(working_board)):
            removed = working_board.chain_length(i, j)
            if removed > 2:
                queue.append(((i, j), removed))
                working_board.remove_chain(i, j)

    if not queue:
        return None
    return max(queue, key=operator.itemgetter(1))

def _parallel_best_first_search_core(board, pool):
    '''Splits the board into four segments and performs best-first search on each.'''
    even = len(board) % 2 == 0
    size = (len(board)/2) if even else (len(board)/2 + 1) # size of each subsquare
    shift = size if even else (size-1) # translation
    boards = []

    boards.append(SameGameBoard([i[:size] for i in board[:size]]))
    boards.append(SameGameBoard([i[shift:] for i in board[:size]]))
    boards.append(SameGameBoard([i[:size] for i in board[shift:]]))
    boards.append(SameGameBoard([i[shift:] for i in board[shift:]]))

    processed = pool.map(_best_first_search_core, boards)
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
        return _best_first_search_core(board)
    return max(results, key=operator.itemgetter(1))

def _parallel_best_n_search_core():
        pass

class SameGame(object):
    def print_main_menu(self):
        print "Welcome to Chainshot!"
        print "====================="
        print "1) Play"
        print "2) Best-first search"
        print "3) Parallel best-first search"
        print "4) Rules"
        print "5) Exit"

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

    def get_main_menu_choice(self):
        print
        try:
            choice = int(raw_input('What would you like to do? '))
            if 0 < choice and choice < 6 :
                return choice
        except:
            pass

        print "I'm sorry, that wasn't a valid choice. Try something else."
        self.print_main_menu()
        return self.get_main_menu_choice()

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
        print self.board

        score = 0
        moves = []
        pool = Pool(4)

        if alg == _parallel_best_first_search_core:
            alg = lambda x: _parallel_best_first_search_core(x, pool)

        start = time.clock()
        while not self.board.end_game():     
            best = alg(self.board)
            moves.append(best[0])
            score += (self.board.remove_chain(*best[0])-2)**2
            self.board = self.board.collapse()
            print
            print self.board
        elapsed = time.clock() - start

        print
        unoccupied = self.board.size() - self.board.occupied()
        percentage = int(float(unoccupied)/self.board.size()*100)
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
        while True:
            self.print_main_menu()
            choice = self.get_main_menu_choice()
            if choice == 1:
                self.play_game(self.get_board())
            elif choice == 2:
                self.best_first_search(self.get_board(), _best_first_search_core)
            elif choice == 3:
                self.best_first_search(self.get_board(), _parallel_best_first_search_core)
            elif choice == 4:
                self.print_rules()
            else:
                break

if __name__ == '__main__':
    sg = SameGame()
    sg.chainshot()
