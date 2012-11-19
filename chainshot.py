#!/usr/bin/python

import os.path

class SameGameBoard(list):
    def __str__(self):
        r = ''
        for i in self:
            r += ''.join([str(j) if j else '*' for j in i])+'\n'
        return r[:-1]

    def occupied(self):
        return len(self)**2 - sum(i.count(None) for i in self)

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
        return -1 if self[row][column] is None else self._chain_length(row, column, SameGameBoard([list(i) for i in self]))

    def remove_chain(self, row, column):
        return -1 if self[row][column] is None else self._chain_length(row, column, self)

    def end_game(self):
        for i in xrange(len(self)-1, 0, -1):
            for j in xrange(len(self)-1, 0, -1):
                if self.chain_length(i, j) > 2:
                    return False
        return True

    def translate_coordinates(self, x, y):
        return (len(self) - x, y - 1)

class SameGame(object):
    def print_main_menu(self):
        print "Welcome to Chainshot!"
        print "====================="
        print "1) Play"
        print "2) Rules"
        print "3) Exit"

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
            if 0 < choice and choice < 4:
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

            if self.board.chain_length(*self.board.translate_coordinates(*move)) < 3:
                raise
            
            return move
        except:
            print 'This move is invalid. Please try again.'

        return self.get_move()
     
    def play_game(self, board_path):
        self.board = SameGameBoard([list(i.strip()) for i in open(board_path, 'r').readlines()])
        print self.board
        score = 0
        while not self.board.end_game():
            move = self.get_move()
            result = (self.board.remove_chain(*self.board.translate_coordinates(*move)) - 2)**2
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
                self.print_rules()
            else:
                break

if __name__ == '__main__':
    sg = SameGame()
    sg.chainshot()
