#!/usr/bin/env ruby

require_relative "engine"

if ARGV.empty?
  warn "Usage: ruby dsmatrix.rb <log_file>"
  exit 1
end

text = File.read(ARGV[0])
results = DSMatrix.analyze(text)
top = results.first

puts "\n=== DSMATRIX RESULT ==="
puts "Top Match: #{top[:name]}"
puts "Score: #{top[:score]}"
puts "\nAll results:"
results.each do |row|
  puts "#{row[:name]} => #{row[:score]}"
end
