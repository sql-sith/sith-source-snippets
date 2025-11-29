# Atoms of Confusion

In programming, an atom of confusion is a small, syntactically correct code snippet that causes programmers to become confused and to slow down or even stop as they read the code. When a programmer encounters an atom of confusion, brain activity increases in the part of the brain that is activated when we read a sentence with a surprising ending.

## Example: unsequenced modifications

The source file `unsequenced_modification.c` is an good example of this. A true C expert might note immediately that the code that assigns a value to `y` is undefined. Most programmers, however would hesitate a bit before deciding either that the postfix operator would have a high precedence (happening after resolving `x` but before the addition, yielding  `y = 1 `), a low priority (so it would happen after the addition altogether, yeilding `y=0 `), or a very high priority (so it would happen before any resolution of x, yielding `y=2`).

```c
#include <stdio.h>

int main() {
    int x = 0;
    int y = x++ + x; // what are x and y after this line?
    printf("x = %d, y = %d\n", x, y);
    return 0;
}
```

### Behavior

I mentioned that for this particular example, the code's behavior is actually undefined. If you compile it with different compilers, you may get different behaviors.

#### MSVC behavior

```PowerShell
# cl 19.50.35719 on PowerShell 7.5.4

❯ cl unsequenced_modification.c /Fe:test_msvc /nologo /W0; .\test_msvc.exe
unsequenced_modification.c
x = 1, y = 0
```

#### gcc behavior

```bash
# gcc (Ubuntu 13.3.0-6ubuntu2~24.04) 13.3.0 on Ubuntu 24.04.3 in WSL 2.5.9.0
❯ gcc -o test_gcc unsequenced_modification.c; ./test_gcc
x = 1, y = 1
```

#### clang behavior:

Notice that `clang`, by default, posts a warning about an "unsequenced modification," but still compiles the program.

```bash

❯ clang unsequenced_modification.c -o test_clang; ./test_clang
unsequenced_modification.c:5:14: warning: unsequenced modification and access to 'x' [-Wunsequenced]
    5 |     int y = x++ + x; // what are x and y after this line?
      |              ^    ~
1 warning generated.
x = 1, y = 1
```

### Summary of compiler differences

|                     | compiles | issues warning |    result    |
| ------------------- | :------: | :------------: | :----------: |
| **cl (msvc)** |   yes   |       no       | x = 1, y = 0 |
| **gcc**       |   yes   |       no       | x = 1, y = 1 |
| **clang**     |   yes   |      yes      | x = 1, y = 1 |
