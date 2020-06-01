import sys

from crossword import *


class CrosswordCreator():

    def __init__(self, crossword):
        """
        Create new CSP crossword generate.
        """
        self.crossword = crossword
        self.domains = {
            var: self.crossword.words.copy()
            for var in self.crossword.variables
        }

    def letter_grid(self, assignment):
        """
        Return 2D array representing a given assignment.
        """
        letters = [
            [None for _ in range(self.crossword.width)]
            for _ in range(self.crossword.height)
        ]
        for variable, word in assignment.items():
            direction = variable.direction
            for k in range(len(word)):
                i = variable.i + (k if direction == Variable.DOWN else 0)
                j = variable.j + (k if direction == Variable.ACROSS else 0)
                letters[i][j] = word[k]
        return letters

    def print(self, assignment):
        """
        Print crossword assignment to the terminal.
        """
        letters = self.letter_grid(assignment)
        for i in range(self.crossword.height):
            for j in range(self.crossword.width):
                if self.crossword.structure[i][j]:
                    print(letters[i][j] or " ", end="")
                else:
                    print("█", end="")
            print()

    def save(self, assignment, filename):
        """
        Save crossword assignment to an image file.
        """
        from PIL import Image, ImageDraw, ImageFont
        cell_size = 100
        cell_border = 2
        interior_size = cell_size - 2 * cell_border
        letters = self.letter_grid(assignment)

        # Create a blank canvas
        img = Image.new(
            "RGBA",
            (self.crossword.width * cell_size,
             self.crossword.height * cell_size),
            "black"
        )
        font = ImageFont.truetype("assets/fonts/OpenSans-Regular.ttf", 80)
        draw = ImageDraw.Draw(img)

        for i in range(self.crossword.height):
            for j in range(self.crossword.width):

                rect = [
                    (j * cell_size + cell_border,
                     i * cell_size + cell_border),
                    ((j + 1) * cell_size - cell_border,
                     (i + 1) * cell_size - cell_border)
                ]
                if self.crossword.structure[i][j]:
                    draw.rectangle(rect, fill="white")
                    if letters[i][j]:
                        w, h = draw.textsize(letters[i][j], font=font)
                        draw.text(
                            (rect[0][0] + ((interior_size - w) / 2),
                             rect[0][1] + ((interior_size - h) / 2) - 10),
                            letters[i][j], fill="black", font=font
                        )

        img.save(filename)

    def solve(self):
        """
        Enforce node and arc consistency, and then solve the CSP.
        """
        self.enforce_node_consistency()
        self.ac3()
        return self.backtrack(dict())

    def enforce_node_consistency(self):
        """
        Update `self.domains` such that each variable is node-consistent.
        (Remove any values that are inconsistent with a variable's unary
         constraints; in this case, the length of the word.)
        """

        # Iterate through all variables in the crossword
        for var in self.domains:
            var_len = var.length

            # Iterate through all values in the variable's domain
            for val in self.domains[var]:
                # If value length does not match variable length, remove value from domain
                if len(val) != var_len:
                    self.domains[var].remove(val)

    def overlap_satisfied(self, x, y, val_x, val_y):
            """
            Helper function that returns true if val_x and val_y
            satisfy any overlap arc consistency requirement for
            variables x and y.

            Returns True if consistency is satisfied, False otherwise.
            """

            # If no overlap, no arc consistency to satisfy
            if not self.crossword.overlaps[x, y]:
                return True

            # Otherwise check that letters match at overlapping indices
            else:
                x_index, y_index = self.crossword.overlaps[x,y]

                if val_x[x_index] == val_y[y_index]:
                    return True
                else:
                    return False

    def revise(self, x, y):
        """
        Make variable `x` arc consistent with variable `y`.
        To do so, remove values from `self.domains[x]` for which there is no
        possible corresponding value for `y` in `self.domains[y]`.

        Return True if a revision was made to the domain of `x`; return
        False if no revision was made.
        """

        revision = False
        to_remove = set()

        # Iterate over domain of x and y, track any inconsistent x:
        for var_x in self.domains[x]:
            consistent = False
            for var_y in self.domains[y]:
                if var_x != var_y and self.overlap_satisfied(x, y, var_x, var_y):
                    consistent = True
                    break

            if not consistent:
                to_remove.add(var_x)
                revision = True

        # Remove any domain variables that aren't arc consistent:
        self.domains[x] = self.domains[x] - to_remove
        return revision

    def ac3(self, arcs=None):
        """
        Update `self.domains` such that each variable is arc consistent.
        If `arcs` is None, begin with initial list of all arcs in the problem.
        Otherwise, use `arcs` as the initial list of arcs to make consistent.

        Return True if arc consistency is enforced and no domains are empty;
        return False if one or more domains end up empty.
        """

        # If no arcs, start with queue of all arcs:
        if not arcs:
            arcs = []
            for var_1 in self.domains:
                for var_2 in self.domains:
                    if var_1 != var_2:
                        arcs.append((var_1, var_2))

        # Continue until no arcs left (arc consistency enforced):
        while arcs.length > 0:
            var_x, var_y = arcs.pop()
            # Revise x domain wrt y:
            if self.revise(var_x, var_y):
                # If x domain is empty after revision, no solution:
                if not self.domains[var_x]:
                    return False
                # If revised, add to arcs all x neighbors
                for var_z in self.crossword.neighbors(var_x) - {var_y}:
                    arcs.append((var_z, var_x))
        return True

    def assignment_complete(self, assignment):
        """
        Return True if `assignment` is complete (i.e., assigns a value to each
        crossword variable); return False otherwise.
        """

        for var in self.domains:
            if var not in assignment:
                return False
        return True

    def consistent(self, assignment):
        """
        Return True if `assignment` is consistent (i.e., words fit in crossword
        puzzle without conflicting characters); return False otherwise.
        """

        used_variables = []

        for var_x in assignment:
            val_x = assignment[var_x]

            # If the assigned word is already used, not consistent:
            if val_x in used_variables:
                return False
            used_variables.append(val_x)

            # Check if variable is assigned its length is correct
            if len(val_x) != var_x.length:
                return False

            # Check if there are conflicts between neighboring variables:
            for var_y in self.crossword.neighbors(var_x):
                if var_y in assignment:
                    val_y = assignment[var_y]

                    # Check if neighbor variable is assigned and satisfies constraints
                    if not self.overlap_satisfied(var_x, var_y, val_x, val_y):
                        return False

        # Otherwise all assignments are consistent
        return True

    def order_domain_values(self, var, assignment):
        """
        Return a list of values in the domain of `var`, in order by
        the number of values they rule out for neighboring variables.
        The first value in the list, for example, should be the one
        that rules out the fewest values among the neighbors of `var`.
        """

        # CURRENTLY RETURN IN ANY ORDER:
        return [x for x in self.domains[var]]

    def select_unassigned_variable(self, assignment):
        """
        Return an unassigned variable not already part of `assignment`.
        Choose the variable with the minimum number of remaining values
        in its domain. If there is a tie, choose the variable with the highest
        degree. If there is a tie, any of the tied variables are acceptable
        return values.
        """

        unassigned = set(self.domains.keys()) - set(assignment.keys())

        # CURRENTLY RETURN FIRST UNASSIGNED IN ANY ORDER:
        for var in unassigned:
            return var

    def backtrack(self, assignment):
        """
        Using Backtracking Search, take as input a partial assignment for the
        crossword and return a complete assignment if possible to do so.

        `assignment` is a mapping from variables (keys) to words (values).

        If no assignment is possible, return None.
        """
        """
        function BACKTRACK(assignment, csp):
 if assignment complete: return assignment
 var = SELECT-UNASSIGNED-VAR(assignment, csp)
 for value in DOMAIN-VALUES(var, assignment, csp):
 if value consistent with assignment:
 add {var = value} to assignment
 inferences = INFERENCE(assignment, csp)
 if inferences ≠ failure: add inferences to assignment
 result = BACKTRACK(assignment, csp)
 if result ≠ failure: return result
 remove {var = value} and inferences from assignment
 return failure
 """
        raise NotImplementedError


def main():

    # Check usage
    if len(sys.argv) not in [3, 4]:
        sys.exit("Usage: python generate.py structure words [output]")

    # Parse command-line arguments
    structure = sys.argv[1]
    words = sys.argv[2]
    output = sys.argv[3] if len(sys.argv) == 4 else None

    # Generate crossword
    crossword = Crossword(structure, words)
    creator = CrosswordCreator(crossword)
    assignment = creator.solve()

    # Print result
    if assignment is None:
        print("No solution.")
    else:
        creator.print(assignment)
        if output:
            creator.save(assignment, output)


if __name__ == "__main__":
    main()
