// assuming envirionment `a`:

// special memory addresses:
// - 0x0: when 1 is written, the program halts
// - 0x1: stdout signal
// - 0x2: stdout trigger (reading value from there produces undefined result) (when 1 is written, writes stdout signal to the buffer, when buffer reaches 16 bits, it is printed as unicode character)
// - 0x3-0xx: the place where your program is located

// valid assumptions:
// - at the start of the program all the memory except for the `special memory addresses`` is filled with zeroes
// - at the start of the program all registers are filled with zeroes
// - the program pointer starts from 0x3

// syntax guide:
// - comment: //
// - labels:
//   - .label - absolute declaration, label name consists of any non-space characters
// - augmentations:
//   - lines that are not started with `.` are forwarded to ./augmenter curr_pos_hex r_dec m_dec {>/?}{line} {*labels}.
//   - when the line is prepended with `?` the augmenter must report with ranges of it's size and required label names in format: {min_hex}-{max_hex} {*labels}, max_hex can be `inf` and *lables is a list of label names delimited by space.
//   - when the line is prepended with `>`, there will be passed additional arguments - *labels hex values (in correspondance to the list returned on `?`) the augmenter must report the result of augmentation that must be binary (if started with 0xb) or hexadecimal (if started with 0x)

reg0: 0x0 = const 0x0               // reg0 must be only 0 or 1, init with 0 (this macro will actually generate no code)
reg1: 0x0 = const 0x2               // set reg1 to 2
reg2: 0x0 = const .msg              // reg2 is the data pointer
reg3: 0x0 = const .loop - .bottom   // reg3 
reg4: 0x0 = const 0x0               // reg4 must be const 0 (this macro will actually generate no code)

.loop

// check pointer reached the end, jmp to halt if so
reg2 == .msgend ? pp = .halt

// read data bit to reg0[0]
reg0[0] = mem[reg2]

// stdout reg0[0] bit
mem[reg0] = reg0[0] // set data
mem[reg1] = 1       // trigger collect

// advance data pointer
reg2++

// jmp to loop
.bottom
reg1[1] ? pp += reg3

.halt
mem[reg4] = 1

.msg
#store_unicode "Hello World"
.msgend