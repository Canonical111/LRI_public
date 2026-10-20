// gen/test_keys.cpp: driver for gen/test_keys.py (A-INV-1). Reads a class file with the generator's own
// read_classes and prints "n NG", then one row "key aut orbit" per class with the key rendered by u128s.
// Exit status 2 and the reader's message on stderr for a malformed file.
#include <iostream>
#include "c8gen.hpp"

int main(int argc, char **argv) {
  if (argc != 2) {
    std::cerr << "usage: test_keys <classes.txt>\n";
    return 2;
  }
  ClassFile cf;
  try {
    cf = read_classes(argv[1]);
  } catch (const InputError &e) {
    std::cerr << e.what() << '\n';
    return 2;
  }
  std::cout << cf.n << ' ' << cf.NG << '\n';
  for (const ClassRow &r : cf.rows) std::cout << u128s(r.key) << ' ' << r.aut << ' ' << r.orbit << '\n';
  return 0;
}
