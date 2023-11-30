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
// - basic instructions:
//   - mem[regN] = <0/1>
//   - mem[regN] ? pp += regK
//   - regN[i] = <0/1>
//   - regN[i] ? pp += regK
//   // any number N/K/i can be decimal/0xb/0x
//   - >0xFF... - insert raw hexadecimal bytes
//   - >0xb01... - insert raw bits
// - labels:
//   - .label - absolute declaration
//   - regN = .label - store the absolute position of the label (with the +3 since code is placed from this offset) (requires label to de declared)
//   - regN = @.label - store the signed distance from this instruction to the label
//   - {any basic instruction} @index.label - relative mark (requires label to be declared and already has no index reserved)
//   - regN = index.label - store the signed distance from relative mark to the label
//   NOTE: regN = .label/index.label generates code that only sets ones, so to ensure correct work it requires register to be filled by zeroes before
// - augmentations:
//   - #name arg1 arg2 "multiword arg" - invokes ./augmenter name current_position_hex r_dec m_dec arg1 arg2
//   - "multiword arg" and substitutes this line with it's stdout, if it exits with non-zero exit code, the whole compilation fails with the response from the invocation
//   - #... @.label ... will insert the hex of the relative position to this label, doest work inside "multiword arg"
//   - the result of augmentation must consist only of basic instructions

// reg0 must have only 0x0 or 0x1 values
reg1[1] = 1 // set reg1 to 0x2
reg2 = .msg // reg2 is the data pointer
reg3 = from_bottom.loop
// reg4 must be const 0x0

.loop

// check pointer reached the end, jmp to halt if so
#eq reg2 @.msgend @.halt 

// read data bit to reg0[0]
#mov reg0[0] mem[reg2]

// stdout reg0[0] bit
mem[reg0] = reg0[0] # set data
mem[reg1] = 1       # trigger collect

// advance data pointer
#inc reg2

// jmp to loop
reg1[1] ? pp += reg3 @from_bottom.loop

.halt
mem[reg4] = 1

.msg
#store_unicode "Hello World"
.msgend