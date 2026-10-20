// gen/test_keys.cpp: driver for gen/test_keys.py (A-INV-1). Reads a class file with the generator's own
// read_classes and prints "n NG", then one row "key aut orbit" per class with the key rendered by u128s.
// With --generator it reads the file as the generator programs do (read_generator_classes: read_classes, then the
// semantic validation validate_generator_classes) and prints the same rows.
// Exit status 2 and the reader's message on stderr for a malformed (or, with --generator, invalid) file.
#include <iostream>
#include "c8gen.hpp"

int main(int argc, char **argv) {
  const bool generator = argc == 3 && std::string(argv[1]) == "--generator";
  if (argc != 2 && !generator) {
    std::cerr << "usage: test_keys [--generator] <classes.txt>\n";
    return 2;
  }
  ClassFile cf;
  try {
    cf = generator ? read_generator_classes(argv[2]) : read_classes(argv[1]);
  } catch (const InputError &e) {
    std::cerr << e.what() << '\n';
    return 2;
  }
  std::cout << cf.n << ' ' << cf.NG << '\n';
  for (const ClassRow &r : cf.rows) std::cout << u128s(r.key) << ' ' << r.aut << ' ' << r.orbit << '\n';
  return 0;
}
