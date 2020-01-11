// This file is part of www.nand2tetris.org
// and the book "The Elements of Computing Systems"
// by Nisan and Schocken, MIT Press.
// File name: projects/04/Mult.asm

// Multiplies R0 and R1 and stores the result in R2.
// (R0, R1, R2 refer to RAM[0], RAM[1], and RAM[2], respectively.)

// Put your code here.

    // Reset answer register
    @R2
    M=0

    // zero check R0
    @R0
    D=M

    @END
    D;JEQ

    // zero check R0
    @R1
    D=M

    @END
    D;JEQ

    // Set counter to value of R1
    @R3
    M=D

// Loop until @R3 is zero
(LOOP)
    @R0
    D=M

    // add R0 + R0
    @R2
    M=M+D
    @R3

    // Decrement R3 counter
    M=M-1
    @R3

    // Jump to LOOP while R3 > 0
    D=M
    @LOOP

    D;JGT
    @END
(END)
    0;JMP


