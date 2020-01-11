// This file is part of www.nand2tetris.org
// and the book "The Elements of Computing Systems"
// by Nisan and Schocken, MIT Press.
// File name: projects/04/Fill.asm

// Runs an infinite loop that listens to the keyboard input.
// When a key is pressed (any key), the program blackens the screen,
// i.e. writes "black" in every pixel;
// the screen should remain fully black as long as the key is pressed. 
// When no key is pressed, the program clears the screen, i.e. writes
// "white" in every pixel;
// the screen should remain fully clear as long as no key is pressed.

    @24576 // Highest addressable memory of SCREEN
           // 16384 + (256 * 32 pixels)
    D=A
    @y
    M=D

(WAIT)
    @KBD // Check KBD Address
    D=M
    @BLACK // Goto BLACK if KBD > 0
    D;JGT
    @CLEAR
    D;JEQ
    @WAIT // Goto WAIT if KB = 0
    0;JMP

(BLACK)
    @color
    M=-1

(DRAWSTART) 
    // Set x = SCREEN
    @SCREEN
    D=A
    @x
    M=D

(DRAWLOOP)
    // Check if we've exhausted memory address range for SCREEN 
    // If true goto WAIT
    @x
    D=M
    @y
    D=M-D

    @WAIT
    D;JEQ

    // Grab the color value
    @color
    D=M

    // Get the value of the x pointer and set to color
    @x
    A=M
    M=D

    // Increment x by one
    @x
    D=M
    M=M+1

    // Continue drawing
    @DRAWLOOP
    0;JMP

(CLEAR)
    // Clear the screen
    @color
    M=0
    @DRAWSTART
    0;JMP
